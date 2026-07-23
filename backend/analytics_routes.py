"""数据分析面板 API"""
from fastapi import APIRouter, Depends
from backend.database import get_connection, get_analytics_summary, get_webhook_stats

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/overview")
async def overview(db=Depends(get_connection)):
    """概览统计"""
    summary = await get_analytics_summary(db)
    wh_stats = await get_webhook_stats(db)
    return {**summary, "webhook_stats": wh_stats}

@router.get("/reasons")
async def reason_distribution(db=Depends(get_connection)):
    """差评原因分布"""
    cursor = await db.execute("""
        SELECT reason_category, COUNT(*) as count
        FROM analyses GROUP BY reason_category ORDER BY count DESC
    """)
    rows = await cursor.fetchall()
    total = sum(r["count"] for r in rows)
    return {
        "distribution": [
            {"category": r["reason_category"], "count": r["count"], "percentage": round(r["count"]/total*100, 1) if total else 0}
            for r in rows
        ]
    }

@router.get("/anger")
async def anger_distribution(db=Depends(get_connection)):
    """愤怒指数分布"""
    cursor = await db.execute("""
        SELECT anger_level, COUNT(*) as count
        FROM analyses GROUP BY anger_level ORDER BY anger_level
    """)
    rows = await cursor.fetchall()
    total = sum(r["count"] for r in rows)
    labels = ["", " 轻微不满", " 失望", " 生气", " 愤怒", " 暴怒"]
    return {
        "distribution": [
            {"level": r["anger_level"], "label": labels[r["anger_level"]] if r["anger_level"] < len(labels) else str(r["anger_level"]), "count": r["count"], "percentage": round(r["count"]/total*100, 1) if total else 0}
            for r in rows
        ]
    }

@router.get("/daily")
async def daily_trend(db=Depends(get_connection)):
    """最近30天每日趋势"""
    cursor = await db.execute("""
        SELECT date(scraped_at) as day, COUNT(*) as scraped_count
        FROM reviews WHERE scraped_at >= date('now','-30 days')
        GROUP BY day ORDER BY day DESC
    """)
    scraped_rows = await cursor.fetchall()
    cursor2 = await db.execute("""
        SELECT date(created_at) as day, COUNT(*) as analyzed_count, ROUND(AVG(anger_level),1) as avg_anger
        FROM analyses WHERE created_at >= date('now','-30 days')
        GROUP BY day ORDER BY day DESC
    """)
    analyzed_rows = await cursor2.fetchall()

    analyzed_map = {r["day"]: r for r in analyzed_rows}
    return {"daily": [
        {"date": r["day"], "scraped": r["scraped_count"],
         "analyzed": dict(analyzed_map.get(r["day"], {})).get("analyzed_count", 0),
         "avg_anger": dict(analyzed_map.get(r["day"], {})).get("avg_anger", 0)}
        for r in scraped_rows
    ]}
