"""A/B 测试 — 挽回邮件变体生成与追踪"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.database import get_connection, create_ab_variant, get_variants_for_review, record_ab_event, get_ab_stats
from backend.ai_agent import ReviewAgent, SYSTEM_PROMPT
from backend.logger import logger

router = APIRouter(prefix="/api/ab", tags=["ab-testing"])

class ABEventRequest(BaseModel):
    variant_id: int
    event_type: str

VARIANT_A_INSTRUCTION = "\n\n<variant_instruction>VARIANT A: Write in a formal, professional tone. Be concise and businesslike. Focus on concrete solutions.</variant_instruction>"
VARIANT_B_INSTRUCTION = "\n\n<variant_instruction>VARIANT B: Write in a warm, personal, empathetic tone. Be conversational. Focus on emotional connection.</variant_instruction>"

@router.post("/generate/{review_id}")
async def generate_variants(review_id: int, db=Depends(get_connection)):
    """为指定评论生成 A/B 两个邮件变体"""
    cursor = await db.execute("SELECT * FROM reviews WHERE id=?", (review_id,))
    row = await cursor.fetchone()
    if not row:
        return {"error": "评论不存在"}
    review = dict(row)

    agent = ReviewAgent()
    results = {}

    for variant_label, instruction in [("A", VARIANT_A_INSTRUCTION), ("B", VARIANT_B_INSTRUCTION)]:
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT + instruction},
                {"role": "user", "content": f"review_text: {review['content']}\ncountry_code: {review['country_code'] or 'US'}\ncustomer_name: {review['reviewer_name']}"}
            ]
            raw = agent._client.chat_with_retry(messages)
            from backend.ai_chain.parser import parse_json_response
            parsed = parse_json_response(raw) or {}
            email = parsed.get("recovery_email", {})
            subject = email.get("subject", "") if isinstance(email, dict) else ""
            body = email.get("body", "") if isinstance(email, dict) else ""

            vid = await create_ab_variant(db, review_id, variant_label, subject, body)
            results[variant_label] = {"id": vid, "subject": subject, "body": body}
        except Exception as e:
            logger.error("生成变体 %s 失败: %s", variant_label, str(e))
            results[variant_label] = {"error": str(e)}

    return {"review_id": review_id, "variants": results}

@router.get("/variants/{review_id}")
async def get_variants(review_id: int, db=Depends(get_connection)):
    variants = await get_variants_for_review(db, review_id)
    return {"review_id": review_id, "variants": variants}

@router.post("/record-event")
async def record_event(body: ABEventRequest, db=Depends(get_connection)):
    await record_ab_event(db, body.variant_id, body.event_type)
    return {"status": "recorded", "event_type": body.event_type}

@router.get("/stats")
async def ab_statistics(db=Depends(get_connection)):
    stats = await get_ab_stats(db)
    return stats
