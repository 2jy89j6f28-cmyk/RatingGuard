"""
Amazon 商品评论爬虫

【功能】
  采集 Amazon 商品的差评（≤3星），输出结构化数据。

【抓取策略】
  直接请求 /product-reviews/{asin}/ 页面，用 BeautifulSoup 解析 HTML 评论容器。
  支持 data-hook 属性和 CSS 类名两种选择器体系。

【使用示例】
  >>> from backend.amazon_scraper import AmazonReviewScraper
  >>> scraper = AmazonReviewScraper()
  >>> reviews = scraper.scrape_product(
  ...     "https://www.amazon.com/dp/B0XXXXXXX"
  ... )
  >>> len(reviews)  # 仅含 ≤3 星的评论
  5

【架构说明】
  - 全流程日志覆盖，每条评论的抽取路径均可追溯
  - 单条评论解析失败不影响整体采集
  - 所有可调参数（延迟、超时、UA）均通过 config 模块注入
  - 内置 TLD→国家码映射表
"""

import re
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

from backend.scraper import Review
from backend.config import settings
from backend.logger import logger
from backend.utils.helpers import get_random_ua, random_delay, retry_on_failure

# ============================================================
# TLD → 国家码映射
# ============================================================

TLD_COUNTRY_MAP = {
    "com":     "US",
    "co.jp":   "JP",
    "de":      "DE",
    "co.uk":   "GB",
    "fr":      "FR",
    "it":      "IT",
    "es":      "ES",
    "ca":      "CA",
    "in":      "IN",
    "com.mx":  "MX",
    "com.au":  "AU",
    "com.br":  "BR",
    "nl":      "NL",
    "se":      "SE",
    "pl":      "PL",
}


# ============================================================
# 爬虫主类
# ============================================================

class AmazonReviewScraper:
    """
    Amazon 商品评论爬虫。

    参数：
        session: 可选的 requests.Session，用于连接复用
    """

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._fixed_ua = settings.scraper_user_agent
        self._delay_min = settings.scraper_delay_min
        self._delay_max = settings.scraper_delay_max
        self._timeout = settings.scraper_timeout

        self.log = logger  # 各方法可直接用 self.log

    # ----------------------------------------------------------
    # 公共入口
    # ----------------------------------------------------------

    def scrape_product(self, product_url: str) -> list[Review]:
        """
        抓取指定 Amazon 商品页的全部评论，返回 ≤3 星的差评列表。

        参数：
            product_url: 商品页完整 URL
                        自动将 /dp/{asin} 转换为 /product-reviews/{asin}/
                        如已是 product-reviews 页面则直接使用

        返回：
            过滤后的 Review 列表，按评分升序排列（差评在前）
        """
        self.log.info("开始抓取 Amazon 商品评论：%s", product_url)

        # 自动转换 URL 到评论页
        reviews_url = self._build_reviews_url(product_url)
        self.log.info("评论页 URL：%s", reviews_url)

        # 从 TLD 推断国家码
        country_code = self._extract_country_from_tld(reviews_url)

        # 抓取页面（捕获异常，失败不崩溃）
        try:
            html = self._fetch_page(reviews_url)
        except Exception as exc:
            self.log.warning("页面抓取失败，返回空列表：%s (%s)", reviews_url, exc)
            return []

        if not html:
            self.log.warning("页面内容为空，跳过：%s", reviews_url)
            return []

        # 解析评论
        try:
            reviews = self._parse_reviews(html, product_url, country_code)
        except Exception as exc:
            self.log.error("评论解析整体失败：%s", exc, exc_info=True)
            return []

        # 过滤并排序
        negative = self._filter_negative(reviews)
        negative.sort(key=lambda r: r.rating)

        self.log.info(
            "抓取完成：共提取 %d 条评论，其中差评 %d 条",
            len(reviews),
            len(negative),
        )
        return negative

    # ----------------------------------------------------------
    # URL 构造 & 工具
    # ----------------------------------------------------------

    def _build_reviews_url(self, url: str) -> str:
        """
        将商品页 URL 自动转换为 /product-reviews/{asin}/ 格式。

        支持的输入格式：
          - https://www.amazon.com/dp/B0XXXXXXX
          - https://www.amazon.com/Name/dp/B0XXXXXXX/
          - https://www.amazon.com/product-reviews/B0XXXXXXX/  (已是目标格式)
          - /dp/B0XXXXXXX                                            (相对路径)
        """
        # 已经是 product-reviews 页面，直接返回
        if "/product-reviews/" in url:
            return url

        # 提取 ASIN
        asin = self._extract_asin(url)
        if not asin:
            self.log.warning("无法从 URL 提取 ASIN，将原样使用：%s", url)
            return url

        # 提取基础 URL（scheme + netloc）
        parsed = urlparse(url)
        if parsed.netloc:
            base = f"{parsed.scheme}://{parsed.netloc}"
        else:
            # 相对路径，默认使用 amazon.com
            base = "https://www.amazon.com"

        return f"{base}/product-reviews/{asin}/"

    @staticmethod
    def _extract_asin(url: str) -> str:
        """
        从 URL 中提取 Amazon ASIN（10 位字母数字）。

        匹配路径模式：/dp/, /product/, /product-reviews/, /gp/product/
        """
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/product/([A-Z0-9]{10})",
            r"/product-reviews/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _extract_country_from_tld(url: str) -> str:
        """
        从 Amazon URL 的顶级域名推断国家码。

        如 amazon.co.jp → JP, amazon.de → DE, amazon.com → US
        """
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()

        # 去除 www. 前缀
        if hostname.startswith("www."):
            hostname = hostname[4:]

        # 按 TLD 长度降序匹配（避免 "co.uk" 被 "uk" 误匹配）
        for tld, code in sorted(TLD_COUNTRY_MAP.items(), key=lambda x: -len(x[0])):
            if hostname == f"amazon.{tld}":
                return code

        # 默认 US
        return "US"

    # ----------------------------------------------------------
    # 页面抓取（含反爬策略）
    # ----------------------------------------------------------

    @retry_on_failure(max_retries=3, exceptions=(requests.RequestException,))
    def _fetch_page(self, url: str) -> str:
        """
        执行 HTTP GET 请求，带反爬保护。

        反爬策略：
          - 每次请求使用不同的 User-Agent
          - 请求间隔随机延时
          - 设置合理的超时时间
          - 3 次指数退避重试
        """
        ua = self._fixed_ua or get_random_ua()
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
        }

        random_delay(self._delay_min, self._delay_max)
        self.log.debug("请求页面：%s (UA: %s…)", url, ua[:40])

        resp = self._session.get(
            url,
            headers=headers,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.text

    # ----------------------------------------------------------
    # HTML 评论解析
    # ----------------------------------------------------------

    def _parse_reviews(
        self, html: str, product_url: str, country_code: str = ""
    ) -> list[Review]:
        """
        解析 Amazon 评论页面 HTML，提取所有评论。

        选择器优先级：
          1. [data-hook="review"]  —— Amazon 官方 data 属性
          2. div.review              —— 通用类名
        """
        soup = BeautifulSoup(html, "lxml")
        reviews: list[Review] = []

        # 主选择器 + 降级
        containers = soup.select('[data-hook="review"]')
        if not containers:
            containers = soup.select("div.review")

        for container in containers:
            try:
                review = self._parse_single_review(
                    container, product_url, country_code
                )
                reviews.append(review)
            except Exception as exc:
                self.log.debug("跳过一条 Amazon 评论：%s", exc)

        self.log.info("HTML 解析共提取 %d 条评论", len(reviews))
        return reviews

    def _parse_single_review(
        self, container: Tag, product_url: str, country_code: str = ""
    ) -> Review:
        """从单个 Amazon 评论 HTML 容器中提取结构化数据。"""
        # --- 评分 ---
        rating = self._extract_rating(container)

        # --- 用户名 ---
        name_el = container.select_one(".a-profile-name")
        reviewer_name = name_el.get_text(strip=True) if name_el else "匿名用户"

        # --- 标题 ---
        title_el = container.select_one('[data-hook="review-title"]')
        if not title_el:
            title_el = container.select_one(".review-title")
        title = title_el.get_text(strip=True) if title_el else ""

        # --- 评论文本 ---
        content_el = container.select_one('[data-hook="review-body"]')
        if not content_el:
            content_el = container.select_one(".review-text-content")
        content = content_el.get_text(strip=True) if content_el else ""

        # --- 日期 ---
        date_el = container.select_one('[data-hook="review-date"]')
        if not date_el:
            date_el = container.select_one(".review-date")
        created_at = date_el.get_text(strip=True) if date_el else ""

        # --- 评论独立 URL ---
        review_url = ""
        permalink = container.select_one('a[data-hook="review-title"]')
        if permalink and permalink.get("href"):
            review_url = permalink["href"]
            if review_url.startswith("/"):
                parsed = urlparse(product_url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                review_url = base + review_url

        return Review(
            reviewer_name=reviewer_name[:80],
            rating=rating,
            title=title[:200],
            content=content[:5000],
            country_code=country_code,
            product_url=product_url,
            review_url=review_url,
            source="amazon-html",
            created_at=created_at,
        )

    # ----------------------------------------------------------
    # 评分提取（核心逻辑）
    # ----------------------------------------------------------

    def _extract_rating(self, container: Tag) -> int:
        """
        从评论容器中提取评分（1-5）。

        支持多种 Amazon 标记格式：
          1. [data-hook="review-star-rating"] 内嵌 .a-icon-alt 文本
          2. .a-icon-alt 独立元素，文本 "3.0 out of 5 stars"
          3. a-star-N CSS 类名模式
        """
        # 方式 1：data-hook="review-star-rating" 容器
        star_el = container.select_one('[data-hook="review-star-rating"]')
        if star_el:
            # 其内部可能有 .a-icon-alt
            alt_el = star_el.select_one(".a-icon-alt")
            if alt_el:
                match = re.search(r"(\d+\.?\d*)\s*out\s*of", alt_el.get_text(strip=True))
                if match:
                    return int(float(match.group(1)))
            # 也可能文本直接在 star_el 上
            match = re.search(r"(\d+\.?\d*)\s*out\s*of", star_el.get_text(strip=True))
            if match:
                return int(float(match.group(1)))

        # 方式 2：.a-icon-alt 独立元素
        icon_el = container.select_one(".a-icon-alt")
        if icon_el:
            match = re.search(r"(\d+\.?\d*)\s*out\s*of", icon_el.get_text(strip=True))
            if match:
                return int(float(match.group(1)))

        # 方式 3：a-star-N 类名模式（如 a-star-4 表示 4 星）
        star_class_el = container.select_one('[class*="a-star-"]')
        if star_class_el:
            classes = " ".join(star_class_el.get("class", []))
            match = re.search(r"a-star-(\d)", classes)
            if match:
                return int(match.group(1))

        return 0

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    @staticmethod
    def _filter_negative(reviews: list[Review]) -> list[Review]:
        """只保留评分 1-3 的差评。"""
        return [r for r in reviews if 1 <= r.rating <= 3]

    def close(self) -> None:
        """释放 HTTP 会话资源。"""
        self._session.close()
