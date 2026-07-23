"use client";

import { useState, useCallback, useEffect } from "react";
import { useRecoveryStream } from "@/hooks/useRecoveryStream";
import { useReviews } from "@/hooks/useReviews";
import { useAuth } from "@/hooks/useAuth";
import LoginModal from "@/components/LoginModal";
import AnalyticsDashboard from "@/components/AnalyticsDashboard";
import type { StreamResult } from "@/hooks/useRecoveryStream";
import type { ProductReview } from "@/lib/api";

/* ═══════════════════════════════════════════════════════════════
   输入模式切换 + 商品 URL 输入栏
   ═══════════════════════════════════════════════════════════════ */

type InputMode = "scrape" | "manual";

function ProductUrlBar({
  onScrape,
  isScraping,
}: {
  onScrape: (url: string) => void;
  isScraping: boolean;
}) {
  const [url, setUrl] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = url.trim();
      if (trimmed && !isScraping) {
        onScrape(trimmed);
      }
    },
    [url, isScraping, onScrape]
  );

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="输入商品 URL 抓取差评..."
        className="flex-1 rounded-lg border border-gray-800 bg-gray-900/50 px-3.5 py-2.5 text-sm text-gray-200 placeholder-gray-600 outline-none transition-colors focus:border-accent/50 focus:bg-gray-900"
        disabled={isScraping}
      />
      <button
        type="submit"
        disabled={isScraping || !url.trim()}
        className={`btn-glow inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
          isScraping
            ? "border-gray-800 bg-gray-800/50 text-gray-500 cursor-not-allowed"
            : "border-accent/40 bg-accent/10 text-accent-light hover:bg-accent/20 hover:shadow-[0_0_20px_-8px_rgba(16,185,129,0.3)]"
        }`}
      >
        {isScraping ? (
          <>
            <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-600 border-t-accent" />
            抓取中…
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path d="M21 21l-6-6m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0z" />
            </svg>
            抓取
          </>
        )}
      </button>
    </form>
  );
}

/* ═══════════════════════════════════════════════════════════════
   手动输入差评表单（免爬虫，直接粘贴差评文本）
   ═══════════════════════════════════════════════════════════════ */

const COUNTRY_OPTIONS = [
  { code: "US", label: "🇺🇸 美国" },
  { code: "GB", label: "🇬🇧 英国" },
  { code: "JP", label: "🇯🇵 日本" },
  { code: "DE", label: "🇩🇪 德国" },
  { code: "FR", label: "🇫🇷 法国" },
  { code: "IT", label: "🇮🇹 意大利" },
  { code: "ES", label: "🇪🇸 西班牙" },
  { code: "KR", label: "🇰🇷 韩国" },
  { code: "BR", label: "🇧🇷 巴西" },
  { code: "AU", label: "🇦🇺 澳大利亚" },
  { code: "NL", label: "🇳🇱 荷兰" },
];

function ManualReviewForm({
  onSubmit,
  isAnalyzing,
}: {
  onSubmit: (params: {
    review_text: string;
    country_code: string;
    customer_name: string;
    rating: number;
    product_title: string;
  }) => void;
  isAnalyzing: boolean;
}) {
  const [text, setText] = useState("");
  const [country, setCountry] = useState("US");
  const [name, setName] = useState("");
  const [rating, setRating] = useState(3);
  const [product, setProduct] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!text.trim() || isAnalyzing) return;
      onSubmit({
        review_text: text.trim(),
        country_code: country,
        customer_name: name.trim() || "Valued Customer",
        rating,
        product_title: product.trim(),
      });
    },
    [text, country, name, rating, product, isAnalyzing, onSubmit]
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* 差评内容 */}
      <div>
        <label className="mb-1 block text-xs text-gray-500">差评内容 *</label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="从卖家后台复制一条差评粘贴到这里..."
          rows={4}
          className="w-full resize-none rounded-lg border border-gray-800 bg-gray-900/50 px-3.5 py-2.5 text-sm text-gray-200 placeholder-gray-600 outline-none transition-colors focus:border-accent/50 focus:bg-gray-900"
          disabled={isAnalyzing}
        />
      </div>

      {/* 评分 */}
      <div>
        <label className="mb-1 block text-xs text-gray-500">评分</label>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setRating(n)}
              className={`h-8 w-8 rounded-md text-sm transition-colors ${
                n <= rating
                  ? "text-amber-400 bg-amber-400/10"
                  : "text-gray-600 bg-gray-800/50"
              }`}
              disabled={isAnalyzing}
            >
              ★
            </button>
          ))}
        </div>
      </div>

      {/* 客户名称 + 国家 */}
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="mb-1 block text-xs text-gray-500">客户名称</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="可选"
            className="w-full rounded-lg border border-gray-800 bg-gray-900/50 px-3.5 py-2 text-sm text-gray-200 placeholder-gray-600 outline-none transition-colors focus:border-accent/50"
            disabled={isAnalyzing}
          />
        </div>
        <div className="w-32">
          <label className="mb-1 block text-xs text-gray-500">国家/地区</label>
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="w-full rounded-lg border border-gray-800 bg-gray-900/50 px-3 py-2 text-sm text-gray-200 outline-none transition-colors focus:border-accent/50"
            disabled={isAnalyzing}
          >
            {COUNTRY_OPTIONS.map((o) => (
              <option key={o.code} value={o.code}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 商品标题 */}
      <div>
        <label className="mb-1 block text-xs text-gray-500">商品标题</label>
        <input
          type="text"
          value={product}
          onChange={(e) => setProduct(e.target.value)}
          placeholder="可选，帮助 AI 更精准分析"
          className="w-full rounded-lg border border-gray-800 bg-gray-900/50 px-3.5 py-2 text-sm text-gray-200 placeholder-gray-600 outline-none transition-colors focus:border-accent/50"
          disabled={isAnalyzing}
        />
      </div>

      <button
        type="submit"
        disabled={isAnalyzing || !text.trim()}
        className={`btn-glow inline-flex w-full items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
          isAnalyzing
            ? "border-gray-800 bg-gray-800/50 text-gray-500 cursor-not-allowed"
            : "border-accent/40 bg-accent/10 text-accent-light hover:bg-accent/20"
        }`}
      >
        {isAnalyzing ? (
          <>
            <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-600 border-t-accent" />
            分析中…
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            开始分析
          </>
        )}
      </button>
    </form>
  );
}

/* ═══════════════════════════════════════════════════════════════
   国家码 → 国旗 + 名称
   ═══════════════════════════════════════════════════════════════ */

const COUNTRY_META: Record<string, { flag: string; label: string }> = {
  US: { flag: "🇺🇸", label: "United States" },
  JP: { flag: "🇯🇵", label: "Japan" },
  GB: { flag: "🇬🇧", label: "United Kingdom" },
  DE: { flag: "🇩🇪", label: "Germany" },
  ES: { flag: "🇪🇸", label: "Spain" },
  FR: { flag: "🇫🇷", label: "France" },
  IT: { flag: "🇮🇹", label: "Italy" },
  KR: { flag: "🇰🇷", label: "South Korea" },
  BR: { flag: "🇧🇷", label: "Brazil" },
};

function getCountryMeta(code: string) {
  return COUNTRY_META[code] ?? { flag: "🌐", label: code };
}

/* ═══════════════════════════════════════════════════════════════
   星级渲染
   ═══════════════════════════════════════════════════════════════ */

function Stars({ rating, max = 5 }: { rating: number; max?: number }) {
  return (
    <span className="inline-flex gap-0.5" aria-label={`${rating} out of ${max} stars`}>
      {Array.from({ length: max }, (_, i) => (
        <span
          key={i}
          className={`text-sm ${
            i < rating ? "text-amber-400" : "text-gray-600"
          }`}
        >
          {i < rating ? "★" : "☆"}
        </span>
      ))}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Toast 通知组件
   ═══════════════════════════════════════════════════════════════ */

function Toast({
  message,
  type = "success",
  visible,
}: {
  message: string;
  type?: "success" | "error";
  visible: boolean;
}) {
  if (!visible) return null;
  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
      <div
        className={`flex items-center gap-2.5 rounded-xl px-5 py-3 text-sm font-medium shadow-xl backdrop-blur-md ${
          type === "success"
            ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
            : "border border-red-500/30 bg-red-500/10 text-red-300"
        }`}
      >
        <span className="text-lg">
          {type === "success" ? "✓" : "✕"}
        </span>
        {message}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   左侧：评论卡片
   ═══════════════════════════════════════════════════════════════ */

function ReviewCard({
  review,
  selected,
  onClick,
}: {
  review: ProductReview;
  selected: boolean;
  onClick: () => void;
}) {
  const country = getCountryMeta(review.country_code);
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border px-4 py-3.5 text-left transition-all duration-200 ${
        selected
          ? "border-accent/50 bg-accent/5 shadow-[0_0_20px_-8px_rgba(16,185,129,0.3)]"
          : "border-gray-800 bg-gray-900/50 hover:border-gray-700 hover:bg-gray-800/50"
      }`}
    >
      {/* 头部：评分 + 国家 */}
      <div className="mb-2 flex items-center justify-between">
        <Stars rating={review.rating} />
        <span className="text-sm text-gray-500" title={country.label}>
          {country.flag}
        </span>
      </div>

      {/* 用户名 */}
      <p className="mb-1 text-sm font-medium text-gray-200">
        {review.reviewer_name}
      </p>

      {/* 评论摘要 */}
      <p className="mb-2 line-clamp-2 text-sm leading-relaxed text-gray-400">
        {review.content}
      </p>

      {/* 底部：日期 + 产品 */}
      <div className="flex items-center justify-between text-xs text-gray-600">
        <span>{review.scraped_at?.slice(0, 10) || ""}</span>
        <span className="truncate max-w-[140px]">{review.product_url}</span>
      </div>
    </button>
  );
}

/* ═══════════════════════════════════════════════════════════════
   右侧：骨架屏（Loading 状态）
   ═══════════════════════════════════════════════════════════════ */

function AnalysisSkeleton() {
  return (
    <div className="space-y-5 animate-fade-in">
      {/* 分析卡片 */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="skeleton-line mb-4 h-4 w-28 rounded" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="skeleton-line h-3 w-16 rounded" />
              <div className="skeleton-line h-4 w-24 rounded" />
            </div>
          ))}
        </div>
      </div>

      {/* 邮件卡片 */}
      <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <div className="skeleton-line mb-3 h-4 w-32 rounded" />
        <div className="skeleton-line mb-2 h-4 w-3/4 rounded" />
        <div className="skeleton-line mb-2 h-4 w-1/2 rounded" />
        <div className="skeleton-line mb-2 h-4 w-5/6 rounded" />
        <div className="skeleton-line mb-2 h-4 w-2/3 rounded" />
        <div className="skeleton-line h-4 w-1/3 rounded" />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   右侧：分析结果卡片
   ═══════════════════════════════════════════════════════════════ */

function AnalysisCard({ result }: { result: StreamResult }) {
  const CATEGORY_LABELS: Record<string, string> = {
    shipping_delay: "📦 物流延迟",
    product_quality: "🏭 产品质量",
    size_fit: "📏 尺码问题",
    damaged_defective: "💔 破损/缺陷",
    customer_service: "💬 客服不满",
    wrong_item: "📦 错发商品",
    not_as_described: "🖼️ 图文不符",
    packaging: "📦 包装问题",
    other: "❓ 其他",
  };

  const ANGER_LABELS = ["", "😊 轻微不满", "🙁 失望", "😠 生气", "😡 愤怒", "🤬 暴怒"];

  return (
    <div className="animate-fade-in rounded-xl border border-gray-800 bg-gray-900/50 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">
        差评分析
      </h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* 根因 */}
        <div>
          <p className="mb-1 text-xs text-gray-500">根因分类</p>
          <p className="text-sm font-medium text-gray-200">
            {CATEGORY_LABELS[result.reason_category] ?? result.reason_category}
          </p>
        </div>
        {/* 愤怒指数 */}
        <div>
          <p className="mb-1 text-xs text-gray-500">愤怒指数</p>
          <div className="flex items-center gap-2">
            <div className="flex h-2 w-24 overflow-hidden rounded-full bg-gray-800">
              <div
                className="h-full rounded-full bg-gradient-to-r from-amber-400 to-red-500 transition-all duration-700"
                style={{ width: `${(result.anger_level / 5) * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium text-gray-300">
              {result.anger_level}/5
            </span>
          </div>
          <p className="mt-0.5 text-xs text-gray-500">
            {ANGER_LABELS[result.anger_level] ?? ""}
          </p>
        </div>
        {/* 沟通风格 */}
        <div>
          <p className="mb-1 text-xs text-gray-500">沟通风格</p>
          <p className="text-sm font-medium text-gray-200 capitalize">
            {result.customer_persona.communication_style}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            {result.customer_persona.cultural_traits}
          </p>
        </div>
      </div>
      {result.customer_persona.suggested_approach && (
        <div className="mt-3 rounded-lg border border-blue-500/20 bg-blue-500/5 px-3.5 py-2">
          <p className="text-xs font-medium text-blue-400">💡 建议策略</p>
          <p className="mt-0.5 text-sm text-gray-300">
            {result.customer_persona.suggested_approach}
          </p>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   右侧：挽回邮件卡片（含打字机效果）
   ═══════════════════════════════════════════════════════════════ */

function EmailCard({
  subject,
  body,
  isStreaming,
}: {
  subject: string;
  body: string;
  isStreaming: boolean;
}) {
  return (
    <div className="animate-fade-in rounded-xl border border-gray-800 bg-gray-900/50 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-500">
        挽回邮件
      </h3>

      {/* 主题 */}
      {subject && (
        <div className="mb-4 rounded-lg border border-gray-700/50 bg-gray-800/50 px-4 py-2.5">
          <p className="text-xs text-gray-500">Subject</p>
          <p className="mt-0.5 text-sm font-medium text-gray-200">{subject}</p>
        </div>
      )}

      {/* 邮件正文 */}
      <div className="relative min-h-[120px]">
        {body ? (
          <div
            className={`whitespace-pre-wrap text-sm leading-relaxed text-gray-300 ${
              isStreaming ? "cursor-blink" : ""
            }`}
          >
            {body}
            {!isStreaming && (
              <div className="mt-3 h-px w-full bg-gradient-to-r from-transparent via-accent/30 to-transparent" />
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center py-12 text-gray-600">
            {isStreaming ? (
              <span className="animate-cursor text-accent">等待内容…</span>
            ) : (
              <span>暂无内容</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   右侧：操作按钮栏（复制 + 发送）
   ═══════════════════════════════════════════════════════════════ */

function ActionBar({ result }: { result: StreamResult }) {
  const [copied, setCopied] = useState(false);
  const [sent, setSent] = useState(false);

  const emailBody = result.recovery_email.body;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(emailBody);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text
      const ta = document.createElement("textarea");
      ta.value = emailBody;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [emailBody]);

  const handleSend = useCallback(() => {
    setSent(true);
    setTimeout(() => setSent(false), 2500);
  }, []);

  return (
    <div className="flex items-center gap-3">
      {/* 复制按钮 */}
      <button
        type="button"
        onClick={handleCopy}
        className={`btn-glow inline-flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-medium transition-all duration-300 ${
          copied
            ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 shadow-[0_0_16px_-6px_rgba(16,185,129,0.4)]"
            : "border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600 hover:bg-gray-700"
        }`}
      >
        {copied ? (
          <>
            <span className="text-emerald-400">✓</span>
            Copied!
          </>
        ) : (
          <>
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            Copy to Clipboard
          </>
        )}
      </button>

      {/* 发送按钮 */}
      <button
        type="button"
        onClick={handleSend}
        className={`btn-glow inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all duration-300 ${
          sent
            ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
            : "border border-accent/40 bg-accent/10 text-accent-light hover:bg-accent/20 hover:shadow-[0_0_20px_-8px_rgba(16,185,129,0.3)]"
        }`}
      >
        {sent ? (
          <>
            <span>✓</span>
            Sent Successfully!
          </>
        ) : (
          <>
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path d="M22 2 11 13" />
              <path d="M22 2 15 22 11 13 2 9 22 2z" />
            </svg>
            Send Email
          </>
        )}
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   右侧面板（空状态 / 加载 / 结果 / 错误）
   ═══════════════════════════════════════════════════════════════ */

function RecoveryPanel({
  selectedReview,
  isStreaming,
  streamedText,
  result,
  error,
}: {
  selectedReview: ProductReview | null;
  isStreaming: boolean;
  streamedText: string;
  result: StreamResult | null;
  error: string | null;
}) {
  // 空状态：未选择评论，也没有流式内容，且无错误
  if (!selectedReview && !isStreaming && !result && !streamedText && !error) {
    return (
      <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-xl border border-dashed border-gray-800 text-center">
        <div className="mb-4 text-4xl text-gray-700">📋</div>
        <p className="text-sm text-gray-500">
          抓取差评或手动粘贴开始分析
        </p>
      </div>
    );
  }

  // Loading 骨架屏（流式传输中也展示骨架，直到收到第一个 token）
  if (!result && !error && !streamedText) {
    return <AnalysisSkeleton />;
  }

  // 错误状态
  if (error && !result) {
    return (
      <div className="flex h-full min-h-[300px] flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 text-center">
        <div className="mb-3 text-3xl">⚠️</div>
        <p className="mb-1 text-sm font-medium text-red-400">分析失败</p>
        <p className="max-w-sm text-xs text-gray-500">{error}</p>
      </div>
    );
  }

  // 有结果（可能是 partial 或 complete）
  return (
    <div className="space-y-4">
      {/* 分析卡片（结果完整时展示） */}
      {result && <AnalysisCard result={result} />}

      {/* 邮件卡片（流式或完成） */}
      <EmailCard
        subject={result?.recovery_email.subject ?? ""}
        body={result ? result.recovery_email.body : streamedText}
        isStreaming={isStreaming}
      />

      {/* 操作按钮（有结果时才显示） */}
      {result && (
        <div className="animate-fade-in pt-1">
          <ActionBar result={result} />
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   ========================== 页面入口 ==========================
   ═══════════════════════════════════════════════════════════════ */

export default function HomePage() {
  const [inputMode, setInputMode] = useState<InputMode>("scrape");
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const { isAuthenticated, username, logout } = useAuth();

  const {
    reviews,
    isLoading,
    isScraping,
    error: scrapeError,
    selectedReview,
    scrapeProduct,
    selectReview,
    loadReviews,
  } = useReviews();
  const { isStreaming, streamedText, result, error: streamError, startStream, reset } =
    useRecoveryStream();

  // 页面加载时自动加载已有评论
  useEffect(() => {
    loadReviews();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 选择已有评论 → 触发流式分析
  const handleSelectReview = useCallback(
    (review: ProductReview) => {
      selectReview(review);
      startStream({
        review_text: review.content,
        country_code: review.country_code,
        customer_name: review.reviewer_name,
        review_id: review.id,
      });
    },
    [selectReview, startStream]
  );

  // 手动输入差评 → 直接流式分析
  const handleManualSubmit = useCallback(
    (params: {
      review_text: string;
      country_code: string;
      customer_name: string;
      rating: number;
      product_title: string;
    }) => {
      selectReview(null); // 清除选择，但 RecoveryPanel 会因 isStreaming 继续展示
      startStream({
        review_text: params.review_text,
        country_code: params.country_code,
        customer_name: params.customer_name,
      });
    },
    [selectReview, startStream]
  );

  // 错误优先显示：流式错误 > 抓取错误
  const displayError = streamError || scrapeError;

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-4 sm:px-6 lg:px-8">
      {/* ── 顶部导航 ── */}
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-blue-500 text-sm font-bold text-white shadow-lg shadow-accent/20">
            RG
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-100">RatingGuard</h1>
            <p className="text-xs text-gray-500">AI 差评挽回特工</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">{username}</span>
              <button
                type="button"
                onClick={logout}
                className="rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-1.5 text-xs text-gray-400 transition-colors hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-400"
              >
                登出
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setAuthModalOpen(true)}
              className="rounded-lg border border-accent/30 bg-accent/5 px-3.5 py-1.5 text-xs font-medium text-accent-light transition-all hover:bg-accent/10 hover:shadow-[0_0_16px_-6px_rgba(16,185,129,0.3)]"
            >
              登录 / 注册
            </button>
          )}
          <button
            type="button"
            onClick={() => setShowAnalytics(!showAnalytics)}
            className={`rounded-lg border px-3 py-1 text-xs font-medium transition-all ${
              showAnalytics
                ? "border-accent/40 bg-accent/10 text-accent-light"
                : "border-gray-700 bg-gray-800/50 text-gray-400 hover:border-gray-600 hover:text-gray-300"
            }`}
          >
             分析
          </button>
          <div className="flex items-center gap-1.5 rounded-full border border-gray-800 bg-gray-900/80 px-3 py-1 text-xs text-gray-500">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]" />
            System Online
          </div>
        </div>
      </header>

      {/* ── 主体：分析面板 / 双栏布局 ── */}
      {showAnalytics ? (
        <AnalyticsDashboard />
      ) : (
      <div className="flex flex-1 flex-col gap-4 lg:flex-row lg:gap-6">
        {/* ========== 左侧：输入区 ========== */}
        <aside className="w-full space-y-3 lg:w-[360px] xl:w-[400px]">
          {/* 模式切换标签页 */}
          <div className="flex rounded-lg border border-gray-800 bg-gray-900/30 p-0.5">
            <button
              type="button"
              onClick={() => setInputMode("scrape")}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
                inputMode === "scrape"
                  ? "bg-gray-800 text-gray-200 shadow-sm"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              🔗 抓取
            </button>
            <button
              type="button"
              onClick={() => setInputMode("manual")}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
                inputMode === "manual"
                  ? "bg-gray-800 text-gray-200 shadow-sm"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              ✏️ 手动输入
            </button>
          </div>

          {inputMode === "scrape" ? (
            <>
              <ProductUrlBar onScrape={scrapeProduct} isScraping={isScraping} />

              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-400">待处理差评</h2>
                <span className="rounded-md bg-gray-800 px-2 py-0.5 text-xs text-gray-500">
                  {reviews.length}
                </span>
              </div>

              <div className="space-y-2.5 overflow-y-auto" style={{ maxHeight: "calc(100vh - 260px)" }}>
                {isLoading ? (
                  <div className="flex items-center justify-center py-12 text-sm text-gray-500">
                    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-700 border-t-accent mr-2" />
                    加载中…
                  </div>
                ) : reviews.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <p className="text-sm text-gray-600">暂无差评数据</p>
                    <p className="mt-1 text-xs text-gray-700">在上方输入商品 URL 开始抓取</p>
                  </div>
                ) : (
                  reviews.map((review) => (
                    <ReviewCard
                      key={review.id}
                      review={review}
                      selected={selectedReview?.id === review.id}
                      onClick={() => handleSelectReview(review)}
                    />
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="overflow-y-auto" style={{ maxHeight: "calc(100vh - 135px)" }}>
              <ManualReviewForm onSubmit={handleManualSubmit} isAnalyzing={isStreaming} />
            </div>
          )}
        </aside>

        {/* ========== 右侧：分析面板 ========== */}
        <main className="flex-1">
          <RecoveryPanel
            selectedReview={selectedReview}
            isStreaming={isStreaming}
            streamedText={streamedText}
            result={result}
            error={displayError}
          />
        </main>
      </div>
      )}

      {/* 登录/注册弹窗 */}
      <LoginModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
      />
    </div>
  );
}
