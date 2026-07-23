"""定时任务调度器 — 自动批量分析未处理的差评"""
import asyncio
from datetime import datetime, timezone
from backend.config import settings
from backend.logger import logger

async def run_scheduled_batch():
    """执行批量分析：扫描所有未分析的差评，逐一调用 AI"""
    import aiosqlite
    from backend.database import get_db_path, update_batch_job, create_batch_job

    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")

        # 查询所有未分析的差评
        cursor = await db.execute("""
            SELECT r.id, r.content, r.country_code, r.reviewer_name
            FROM reviews r
            LEFT JOIN analyses a ON r.id = a.review_id
            WHERE a.id IS NULL AND r.is_negative = 1
            LIMIT 50
        """)
        rows = await cursor.fetchall()

        if not rows:
            logger.info("无可分析的差评")
            return {"processed": 0}

        job_id = await create_batch_job(db, "batch_analysis", len(rows))
        logger.info("开始批量分析 %d 条差评", len(rows))

        from backend.ai_agent import ReviewAgent
        agent = ReviewAgent()
        completed = 0

        for row in rows:
            try:
                result = agent.analyze(
                    review_text=row["content"],
                    country_code=row["country_code"] or "",
                    customer_name=row["reviewer_name"]
                )
                # 持久化结果
                from backend.database import upsert_analysis
                await upsert_analysis(db, row["id"], result,
                    result.get("rawText", ""), settings.deepseek_model)
                completed += 1
            except Exception as e:
                logger.error("分析失败 review_id=%d: %s", row["id"], e)

            await update_batch_job(db, job_id, completed=completed)

        await update_batch_job(db, job_id, status="completed", completed=completed)
        logger.info("批量分析完成: %d/%d", completed, len(rows))
        return {"processed": completed, "total": len(rows)}

_scheduler_task = None

async def scheduler_loop():
    """主循环：每60秒检查一次是否需要执行"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            # 每个整点执行一次（简化版调度）
            if now.minute == 0:
                logger.info("触发定时批量分析")
                await run_scheduled_batch()
            await asyncio.sleep(60)
        except Exception as e:
            logger.error("调度器异常: %s", e)
            await asyncio.sleep(60)

def start_scheduler():
    global _scheduler_task
    loop = asyncio.get_event_loop()
    _scheduler_task = loop.create_task(scheduler_loop())
    logger.info("定时调度器已启动 (每60分钟检查)")

async def stop_scheduler():
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        logger.info("定时调度器已停止")
