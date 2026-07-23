"""
FastAPI 应用入口 —— 流式 AI 差评挽回接口

╔══════════════════════════════════════════════════════════════════╗
║  GET  /health                     健康检查                      ║
║  POST /api/stream-recovery        SSE 流式差评分析 + 挽回信     ║
║  POST /api/scrape                 触发爬虫抓取差评              ║
║  GET  /api/reviews                评论列表                      ║
║  GET  /api/reviews/{id}           评论详情 + 分析结果           ║
╚══════════════════════════════════════════════════════════════════╝

【SSE 事件流协议】
  客户端通过 fetch + ReadableStream 消费以下事件：

  事件类型      data 格式                             触发时机
  ────────     ──────────────────────────────────    ───────────
  token        {"type":"token","content":"Dear "}    每个 delta chunk
  done         {"type":"done","result":{...}}        流结束，含完整结构化结果
  error        {"type":"error","message":"..."}      发生不可恢复错误

【使用示例】
  curl -N -X POST http://localhost:8000/api/stream-recovery \\
    -H "Content-Type: application/json" \\
    -d '{
      "review_text": "The shoes arrived broken",
      "country_code": "US",
      "customer_name": "Sarah"
    }'
"""

import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.logger import logger
from backend.ai_agent import SYSTEM_PROMPT, validate_agent_response

# ═════════════════════════════════════════════════════════════════
#  Pydantic 请求/响应模型
# ═════════════════════════════════════════════════════════════════

from pydantic import BaseModel


class RecoveryRequest(BaseModel):
    """前端发起差评分析请求时提交的荷载。"""
    review_text: str
    country_code: str = ""
    customer_name: str = "Valued Customer"
    rating: int | None = None
    product_title: str | None = None
    review_id: int | None = None          # 数据库中的评论 ID（用于持久化分析结果）


# ═════════════════════════════════════════════════════════════════
#  Lifespan —— 启动/关闭生命周期
# ═════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库，启动定时调度器；关闭时停止调度器。"""
    from backend.database import init_db
    from backend.scheduler import start_scheduler, stop_scheduler

    await init_db(settings.database_path)
    logger.info("数据库已就绪: %s", settings.database_path)

    start_scheduler()

    yield

    await stop_scheduler()


# ═════════════════════════════════════════════════════════════════
#  FastAPI 实例初始化 + CORS
# ═════════════════════════════════════════════════════════════════

# 解析 CORS 来源（支持逗号分隔）
_cors_origins = [
    o.strip()
    for o in settings.cors_origins.split(",")
    if o.strip()
]
if not _cors_origins:
    _cors_origins = ["http://localhost:3000"]

app = FastAPI(
    title="RatingGuard — AI 差评挽回 API",
    description="流式 AI 差评分析与多语言挽回邮件生成服务",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═════════════════════════════════════════════════════════════════
#  注册路由器
# ═════════════════════════════════════════════════════════════════

from backend.scrape_routes import router as scrape_router
from backend.review_routes import router as review_router
from backend.batch_routes import router as batch_router
from backend.webhook_routes import router as webhook_router
from backend.auth import router as auth_router
from backend.ab_routes import router as ab_router
from backend.analytics_routes import router as analytics_router
app.include_router(scrape_router)
app.include_router(review_router)
app.include_router(batch_router)
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(ab_router)
app.include_router(analytics_router)


# ═════════════════════════════════════════════════════════════════
#  健康检查
# ═════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """健康检查探针。"""
    return {
        "status": "ok",
        "database": "connected",
        "model": settings.deepseek_model or "not_configured",
        "shopify_domain": settings.shopify_domain or "not_configured",
    }


# ═════════════════════════════════════════════════════════════════
#  SSE 流式生成器
# ═════════════════════════════════════════════════════════════════

async def _stream_analysis(
    review_text: str,
    country_code: str,
    customer_name: str,
    review_id: int | None = None,         # 持久化用
) -> AsyncGenerator[str, None]:
    """
    SSE 事件流生成器。

    内部步骤：
      1. 拼接 messages（与 ReviewAgent._build_messages 一致）
      2. 调用 DeepSeek API + stream=True
      3. 每收到一个 token 立即 yield SSE 事件
      4. 流结束后，将累积文本解析为 JSON，yield done 事件

    异常处理：
      - API Key 未配置 → error 事件
      - 网络错误      → error 事件
      - JSON 解析失败  → 通过 done 事件携带 rawText 字段降级
    """
    # ── Step 1: 校验 API Key ──────────────────────────────
    if not settings.deepseek_api_key:
        yield _sse_event("error", {
            "message": "DEEPSEEK_API_KEY 未配置。请在 .env 文件中设置。",
        })
        return

    # ── Step 2: 构造 messages（Caching 友好） ──────────────
    extra_context = ""
    if customer_name:
        extra_context += f"customer_name: {customer_name}\n"

    user_content = (
        f"review_text: {review_text}\n"
        f"country_code: {country_code or 'unknown'}\n"
        f"{extra_context}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # ── Step 3: 初始化 AsyncOpenAI（延迟导入，容错） ───────
    try:
        from openai import AsyncOpenAI as _AsyncOpenAI
        client = _AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    except ImportError:
        yield _sse_event("error", {
            "message": "openai SDK 未安装。请执行: pip install openai",
        })
        return

    # ── Step 4: 发起流式请求 ─────────────────────────────
    accumulated = ""
    token_count = 0

    try:
        stream = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            stream=True,
        )

        async for chunk in stream:
            # 提取 delta 文本
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if not delta:
                continue

            accumulated += delta
            token_count += 1

            # 每 3 个 token 或遇到句号/换行时 flush，减少前端重绘频率
            # 但仍然保持实时性
            yield _sse_event("token", {"content": delta})

            # 记录日志（采样，避免刷屏）
            if token_count % 50 == 0:
                logger.info(
                    "流式传输中: %d tokens (%d chars)",
                    token_count,
                    len(accumulated),
                )

    except Exception as e:
        logger.error("DeepSeek 流式调用异常: %s", str(e), exc_info=True)
        yield _sse_event("error", {
            "message": f"AI 服务调用失败: {type(e).__name__}",
        })
        return

    # ── Step 5: 流结束，解析累积 JSON ─────────────────────
    logger.info(
        "流式传输完成: %d tokens → %d chars",
        token_count,
        len(accumulated),
    )

    # 尝试解析 JSON
    result = _try_parse_accumulated(accumulated)

    yield _sse_event("done", result)

    # ── Step 6: 如果提供了 review_id，持久化分析结果 ─────
    if review_id is not None:
        try:
            from backend.database import upsert_analysis
            from backend.config import settings as _cfg

            # 使用独立连接（避免与请求生命周期冲突）
            db_path = _cfg.database_path
            async with aiosqlite.connect(db_path) as _db:
                await _db.execute("PRAGMA journal_mode=WAL")
                _db.row_factory = None
                await upsert_analysis(
                    _db, review_id, result, accumulated, _cfg.deepseek_model
                )
            logger.info("分析结果已持久化 — review_id=%d", review_id)
        except Exception as _e:
            logger.warning("分析结果持久化失败: %s", _e)


def _try_parse_accumulated(raw: str) -> dict:
    """
    将流式累积的原始文本解析为结构化结果。

    使用 ai_chain.parser 的 parse_json_response 智能提取 JSON，
    并调用 validate_agent_response 补全缺失字段。

    参数：
        raw: LLM 输出的原始累积文本

    返回：
        包含以下键的字典：
          - reason_category / anger_level / customer_persona / recovery_email
          （结构分析成功时从 JSON 提取）
          - rawText（始终包含，供前端兜底展示）
    """
    from backend.ai_chain.parser import parse_json_response
    from backend.ai_agent import validate_agent_response

    parsed = parse_json_response(raw)

    if parsed:
        validated = validate_agent_response(parsed)
        validated["rawText"] = raw
        return validated

    # JSON 完全不可解析 → 保底返回
    logger.warning("流式累积文本无法解析为 JSON，返回保底结构")
    return {
        "reason_category": "other",
        "anger_level": 3,
        "customer_persona": {
            "communication_style": "unknown",
            "cultural_traits": "",
            "suggested_approach": "",
        },
        "recovery_email": {
            "subject": "We're sorry about your experience",
            "body": raw,  # 将原始文本作为邮件体展示
            "language": "en",
        },
        "rawText": raw,
    }


def _sse_event(event_type: str, data: dict) -> str:
    """
    构造 SSE 协议格式的字符串。

    参数：
        event_type: 事件类型（token / done / error）
        data: 要序列化为 JSON 的数据负载

    返回：
        符合 SSE 协议的字符串：`data: {...}\n\n`
    """
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ═════════════════════════════════════════════════════════════════
#  业务路由
# ═════════════════════════════════════════════════════════════════

@app.post("/api/stream-recovery")
async def stream_recovery(body: RecoveryRequest, request: Request):
    """
    【流式】AI 差评分析与挽回邮件生成。

    接收差评文本 → 实时流式调用 DeepSeek → SSE 推送每个 token →
    完成后推送结构化结果。

    请求体：
      - review_text:   差评原文（必填）
      - country_code:  ISO 国家码，如 US / JP / DE（选填）
      - customer_name: 客户名称（选填，用于邮件称呼）
      - rating:        评分 1-5（选填，供 AI 参考）
      - product_title: 商品标题（选填，供 AI 参考）

    响应：
      text/event-stream 格式的 SSE 事件流。
    """
    logger.info(
        "收到流式分析请求 — country=%s | customer=%s | text_len=%d",
        body.country_code or "unknown",
        body.customer_name,
        len(body.review_text),
    )

    return StreamingResponse(
        _stream_analysis(
            review_text=body.review_text,
            country_code=body.country_code,
            customer_name=body.customer_name,
            review_id=body.review_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


# ═════════════════════════════════════════════════════════════════
#  直接启动入口
# ═════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    logger.info("启动 RatingGuard API 服务 — http://0.0.0.0:8000")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,         # 开发模式热重载
        log_level="info",
    )
