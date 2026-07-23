"""Webhook 集成 — Slack + 自定义邮件"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.database import get_connection, create_webhook, get_active_webhooks, delete_webhook, log_webhook_delivery
from backend.logger import logger

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

class WebhookCreate(BaseModel):
    name: str
    webhook_type: str = "slack"
    url: str

class WebhookTest(BaseModel):
    pass

@router.get("")
async def list_webhooks(db=Depends(get_connection)):
    whs = await get_active_webhooks(db)
    return {"webhooks": whs}

@router.post("")
async def add_webhook(body: WebhookCreate, db=Depends(get_connection)):
    wid = await create_webhook(db, body.name, body.webhook_type, body.url)
    return {"id": wid, "status": "created"}

@router.delete("/{webhook_id}")
async def remove_webhook(webhook_id: int, db=Depends(get_connection)):
    await delete_webhook(db, webhook_id)
    return {"status": "deleted"}

@router.post("/test/{webhook_id}")
async def test_webhook(webhook_id: int, db=Depends(get_connection)):
    # 获取 webhook 信息并测试
    cursor = await db.execute("SELECT * FROM webhooks WHERE id=?", (webhook_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "Webhook 不存在")
    wh = dict(row)
    try:
        if wh["webhook_type"] == "slack":
            async with httpx.AsyncClient() as client:
                resp = await client.post(wh["url"], json={
                    "text": "✅ RatingGuard Webhook 测试成功！\n您的 Webhook 配置正确。"
                }, timeout=10)
                await log_webhook_delivery(db, webhook_id, "success" if resp.status_code in (200,204) else "failed", resp.status_code)
                return {"status": "ok", "code": resp.status_code}
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.post(wh["url"], json={
                    "subject": "RatingGuard Webhook 测试", "body": "测试邮件内容"
                }, timeout=10)
                await log_webhook_delivery(db, webhook_id, "success" if resp.status_code in (200,201,202,204) else "failed", resp.status_code)
                return {"status": "ok", "code": resp.status_code}
    except Exception as e:
        await log_webhook_delivery(db, webhook_id, "failed", 0, str(e))
        raise HTTPException(502, f"Webhook 请求失败: {e}")

# 导出 dispatch 函数供 ActionBar 使用
async def dispatch_webhooks(email_subject: str, email_body: str, review_info: dict, db) -> list:
    """向所有激活的 webhook 发送通知"""
    whs = await get_active_webhooks(db)
    results = []
    for wh in whs:
        try:
            if wh["webhook_type"] == "slack":
                payload = {
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": f":email: 挽回邮件已发送: {email_subject}"}},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"*收件人:* {review_info.get('customer_name','N/A')}\n*国家:* {review_info.get('country_code','N/A')}"}},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"```{email_body[:1000]}```"}},
                    ]
                }
                async with httpx.AsyncClient() as c:
                    resp = await c.post(wh["url"], json=payload, timeout=10)
            else:
                async with httpx.AsyncClient() as c:
                    resp = await c.post(wh["url"], json={
                        "to": review_info.get("customer_email",""), "subject": email_subject, "body": email_body
                    }, timeout=10)
            await log_webhook_delivery(db, wh["id"], "success" if resp.status_code < 400 else "failed", resp.status_code)
            results.append({"webhook_id": wh["id"], "status": "success"})
        except Exception as e:
            await log_webhook_delivery(db, wh["id"], "failed", 0, str(e))
    return results
