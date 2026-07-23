"use client";
import { useState, useEffect } from "react";

interface Overview {
  total_reviews: number;
  analyzed_reviews: number;
  avg_anger: number;
  top_reasons: { category: string; count: number }[];
}

interface ReasonDist {
  distribution: { category: string; count: number; percentage: number }[];
}

interface AngerDist {
  distribution: { level: number; label: string; count: number; percentage: number }[];
}

const CATEGORY_LABELS: Record<string, string> = {
  shipping_delay: " 物流延迟", product_quality: " 产品质量",
  size_fit: " 尺码问题", damaged_defective: " 破损",
  customer_service: " 客服", wrong_item: " 错发",
  not_as_described: " 图文不符", packaging: " 包装", other: " 其他",
};

export default function AnalyticsDashboard() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [reasons, setReasons] = useState<ReasonDist | null>(null);
  const [angers, setAngers] = useState<AngerDist | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [ov, rs, ag] = await Promise.all([
          fetch("/api/analytics/overview").then(r => r.json()),
          fetch("/api/analytics/reasons").then(r => r.json()),
          fetch("/api/analytics/anger").then(r => r.json()),
        ]);
        setOverview(ov); setReasons(rs); setAngers(ag);
      } catch (e) { console.error(e); }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return (
    <div className="animate-pulse space-y-4 px-4">
      <div className="h-20 bg-gray-800 rounded-xl"/>
      <div className="h-32 bg-gray-800 rounded-xl"/>
      <div className="h-32 bg-gray-800 rounded-xl"/>
    </div>
  );

  return (
    <div className="space-y-6 p-4 animate-fade-in">
      <h2 className="text-lg font-bold text-gray-200"> 数据分析面板</h2>

      {/* 概览卡片 */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="总差评数" value={overview.total_reviews} icon=" " />
          <StatCard label="已分析" value={overview.analyzed_reviews} icon=" " />
          <StatCard label="平均愤怒值" value={overview.avg_anger?.toFixed(1)} icon=" " />
          <StatCard label="挽回率" value={`${overview.analyzed_reviews ? Math.round(overview.analyzed_reviews / Math.max(overview.total_reviews, 1) * 100) : 0}%`} icon=" " />
        </div>
      )}

      {/* 原因分布 */}
      {reasons && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <h3 className="mb-4 text-sm font-semibold text-gray-400">差评原因分布</h3>
          <div className="space-y-3">
            {reasons.distribution.map(r => (
              <div key={r.category} className="flex items-center gap-3">
                <span className="w-24 text-xs text-gray-400">{CATEGORY_LABELS[r.category] || r.category}</span>
                <div className="flex-1 h-5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-accent to-blue-500 rounded-full transition-all duration-700" style={{ width: `${r.percentage}%` }} />
                </div>
                <span className="w-12 text-right text-xs text-gray-500">{r.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 愤怒指数分布 */}
      {angers && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
          <h3 className="mb-4 text-sm font-semibold text-gray-400">愤怒指数分布</h3>
          <div className="space-y-3">
            {angers.distribution.map(a => (
              <div key={a.level} className="flex items-center gap-3">
                <span className="w-28 text-xs text-gray-400">{a.label}</span>
                <div className="flex-1 h-5 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-amber-400 to-red-500 rounded-full transition-all duration-700" style={{ width: `${a.percentage}%` }} />
                </div>
                <span className="w-12 text-right text-xs text-gray-500">{a.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: string | number; icon: string }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
      <p className="text-2xl mb-1">{icon}</p>
      <p className="text-2xl font-bold text-gray-200">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}
