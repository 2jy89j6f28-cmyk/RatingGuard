"""
爬虫 API 路由 —— 触发 Shopify 差评抓取

POST /api/scrape  — 接受商品 URL，运行爬虫，结果写入数据库
"""

from urllib.parse import urlparse
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.database import get_connection, upsert_product, insert_reviews
from backend.scraper import ShopifyReviewScraper
from backend.amazon_scraper import AmazonReviewScraper
from backend.config import settings
from backend.logger import logger

router = APIRouter(prefix="/api", tags=["scrape"])


class ScrapeRequest(BaseModel):
    """爬虫触发请求。"""
    product_url: str
    platform: str = "shopify"  # "shopify" 或 "amazon"


class ScrapeResponse(BaseModel):
    """爬虫响应。"""
    status: str
    product_id: int | None = None
    reviews_count: int = 0
    message: str = ""


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_product(body: ScrapeRequest, db=Depends(get_connection)):
    """
    抓取指定商品页的全部评论，过滤出 ≤3 星差评并存入数据库。

    请求体：
      - product_url: 商品页完整 URL 或相对路径（如 /products/handle）
      - platform:    "shopify"（默认）或 "amazon"
    """
    url = body.product_url
    platform = body.platform
    logger.info("收到爬虫请求: platform=%s, url=%s", platform, url)

    # ---- 根据平台初始化爬虫与域名 ----
    if platform == "amazon":
        # Amazon：由爬虫内部处理 URL 转换
        domain = urlparse(url).netloc or "www.amazon.com"
        scraper = AmazonReviewScraper()
    else:
        # Shopify：补全相对路径
        if url.startswith("/"):
            if not settings.shopify_domain:
                raise HTTPException(
                    status_code=400,
                    detail="使用了相对路径但 SHOPIFY_STORE_DOMAIN 未配置。请传入完整 URL 或配置 .env。",
                )
            url = f"https://{settings.shopify_domain}{url}"
        parsed = urlparse(url)
        domain = parsed.netloc or settings.shopify_domain
        scraper = ShopifyReviewScraper()

    # 执行爬虫（同步操作放到线程池，避免阻塞事件循环）
    try:
        reviews = await asyncio.to_thread(scraper.scrape_product, url)
    except Exception as e:
        logger.error("爬虫异常: %s", e, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"抓取失败: {type(e).__name__}: {e}",
        )
    finally:
        scraper.close()

    if not reviews:
        return ScrapeResponse(
            status="success",
            product_id=None,
            reviews_count=0,
            message="未找到差评（≤3星）。页面可能没有评论或评论解析策略未命中。",
        )

    # 写入数据库
    product_id = await upsert_product(db, url, domain)
    ids = await insert_reviews(db, product_id, reviews)

    return ScrapeResponse(
        status="success",
        product_id=product_id,
        reviews_count=len(ids),
        message=f"成功抓取 {len(ids)} 条差评",
    )
