"""批量处理 API 路由"""
from fastapi import APIRouter, Depends, BackgroundTasks
from backend.database import get_connection, get_batch_jobs
from backend.scheduler import run_scheduled_batch
from backend.logger import logger

router = APIRouter(prefix="/api/batch", tags=["batch"])

@router.post("/analyze")
async def trigger_batch_analysis(background_tasks: BackgroundTasks):
    """手动触发批量分析（后台执行）"""
    background_tasks.add_task(run_scheduled_batch)
    return {"status": "started", "message": "批量分析已触发"}

@router.get("/jobs")
async def list_batch_jobs(limit: int = 20, db=Depends(get_connection)):
    jobs = await get_batch_jobs(db, limit)
    return {"jobs": jobs, "total": len(jobs)}

@router.get("/status")
async def batch_status(db=Depends(get_connection)):
    """获取批量处理统计"""
    cursor = await db.execute("""
        SELECT r.id FROM reviews r
        LEFT JOIN analyses a ON r.id = a.review_id
        WHERE a.id IS NULL AND r.is_negative = 1
    """)
    pending = len(await cursor.fetchall())
    cursor2 = await db.execute("SELECT COUNT(*) as c FROM analyses")
    total_analyzed = (await cursor2.fetchone())[0]
    return {"pending_reviews": pending, "total_analyzed": total_analyzed}
