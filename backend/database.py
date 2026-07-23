"""
异步 SQLite 数据库层

为 RatingGuard 提供持久化存储：
  - products   商品表（从 URL 去重）
  - reviews    差评表（每条爬取的评论）
  - analyses   分析结果表（AI 生成的结构化结果）

所有数据库操作通过 FastAPI Depends(get_connection) 注入。
"""

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from typing import AsyncGenerator

import aiosqlite

from backend.config import settings
from backend.logger import logger

# ============================================================
#  数据库路径
# ============================================================

def get_db_path() -> str:
    """返回数据库文件路径，可通过 DATABASE_PATH 环境变量覆盖。"""
    return settings.database_path or os.path.join(
        os.getcwd(), "ratingguard.db"
    )


# ============================================================
#  初始化（建表 + WAL 模式）
# ============================================================

_SQL_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT NOT NULL UNIQUE,
    domain      TEXT NOT NULL DEFAULT '',
    title       TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    reviewer_name   TEXT DEFAULT '匿名用户',
    rating          INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    title           TEXT DEFAULT '',
    content         TEXT DEFAULT '',
    country_code    TEXT DEFAULT '',
    product_url     TEXT DEFAULT '',
    review_url      TEXT DEFAULT '',
    source          TEXT DEFAULT 'unknown',
    original_date   TEXT DEFAULT '',
    scraped_at      TEXT NOT NULL,
    is_negative     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analyses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id           INTEGER NOT NULL UNIQUE REFERENCES reviews(id) ON DELETE CASCADE,
    reason_category     TEXT DEFAULT 'other',
    anger_level         INTEGER DEFAULT 3 CHECK(anger_level >= 1 AND anger_level <= 5),
    communication_style TEXT DEFAULT '',
    cultural_traits     TEXT DEFAULT '',
    suggested_approach  TEXT DEFAULT '',
    email_subject       TEXT DEFAULT '',
    email_body          TEXT DEFAULT '',
    email_language      TEXT DEFAULT 'en',
    raw_llm_output      TEXT DEFAULT '',
    model_used          TEXT DEFAULT '',
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_analyses_review_id ON analyses(review_id);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS batch_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL DEFAULT 'batch_analysis',
    status TEXT NOT NULL DEFAULT 'pending',
    total_items INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,
    error_message TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    webhook_type TEXT NOT NULL DEFAULT 'slack',
    url TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ab_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    variant_label TEXT NOT NULL,
    email_subject TEXT DEFAULT '',
    email_body TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ab_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL REFERENCES ab_variants(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id INTEGER NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    response_code INTEGER DEFAULT 0,
    error_message TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ab_variants_review_id ON ab_variants(review_id);
CREATE INDEX IF NOT EXISTS idx_ab_events_variant_id ON ab_events(variant_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);
"""


async def init_db(db_path: str | None = None) -> None:
    """初始化数据库：创建表 + 启用 WAL 模式。幂等操作。"""
    path = db_path or get_db_path()
    logger.info("初始化数据库: %s", path)

    try:
        async with aiosqlite.connect(path) as db:
            # WAL 模式 —— 允许并发读
            await db.execute("PRAGMA journal_mode=WAL")
            await db.executescript(_SQL_CREATE_TABLES)
            await db.commit()
        logger.info("数据库初始化完成")
    except PermissionError:
        logger.warning("数据库目录不可写，回退到 :memory:")
    except Exception as e:
        logger.error("数据库初始化失败: %s", e, exc_info=True)
        raise


# ============================================================
#  连接依赖（FastAPI 用）
# ============================================================

async def get_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    FastAPI 依赖项：提供异步数据库连接。

    使用方式：
        @app.get("/items")
        async def list_items(db=Depends(get_connection)):
            ...
    """
    path = get_db_path()
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        db.row_factory = sqlite3.Row
        yield db


# ============================================================
#  Products CRUD
# ============================================================

async def upsert_product(
    db: aiosqlite.Connection,
    url: str,
    domain: str = "",
    title: str = "",
) -> int:
    """
    插入或忽略商品（按 URL 去重）。返回商品 ID。
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    cursor = await db.execute(
        """
        INSERT INTO products (url, domain, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            domain=excluded.domain,
            title=CASE WHEN excluded.title != '' THEN excluded.title ELSE products.title END,
            updated_at=excluded.updated_at
        """,
        (url, domain, title, now, now),
    )
    await db.commit()

    # 获取 ID（INSERT 或 SELECT）
    cursor2 = await db.execute("SELECT id FROM products WHERE url = ?", (url,))
    row = await cursor2.fetchone()
    return row["id"] if row else cursor.lastrowid


# ============================================================
#  Reviews CRUD
# ============================================================

async def insert_reviews(
    db: aiosqlite.Connection,
    product_id: int,
    reviews: list,
) -> list[int]:
    """
    批量插入评论。返回插入的 ID 列表。
    通过 (reviewer_name, content[:50], product_id) 去重。
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    ids: list[int] = []

    for r in reviews:
        is_neg = 1 if 1 <= r.rating <= 3 else 0
        try:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO reviews
                    (product_id, reviewer_name, rating, title, content,
                     country_code, product_url, review_url, source,
                     original_date, scraped_at, is_negative)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    r.reviewer_name,
                    r.rating,
                    r.title,
                    r.content,
                    r.country_code,
                    r.product_url,
                    r.review_url,
                    r.source,
                    r.created_at,
                    now,
                    is_neg,
                ),
            )
            if cursor.lastrowid:
                ids.append(cursor.lastrowid)
        except Exception as e:
            logger.warning("插入评论失败: %s", e)

    await db.commit()
    return ids


async def get_reviews(
    db: aiosqlite.Connection,
    product_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    negative_only: bool = True,
) -> list[dict]:
    """
    获取评论列表。默认只返回差评（≤3星），按抓取时间倒序。
    """
    parts = ["SELECT * FROM reviews WHERE 1=1"]
    params = []

    if product_id is not None:
        parts.append("AND product_id = ?")
        params.append(product_id)
    if negative_only:
        parts.append("AND is_negative = 1")

    parts.append("ORDER BY scraped_at DESC LIMIT ? OFFSET ?")
    params.extend([limit, offset])

    cursor = await db.execute(" ".join(parts), params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_review_by_id(
    db: aiosqlite.Connection,
    review_id: int,
) -> dict | None:
    """通过 ID 查询单条评论。"""
    cursor = await db.execute(
        "SELECT * FROM reviews WHERE id = ?", (review_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


# ============================================================
#  Analyses CRUD
# ============================================================

async def get_analysis_by_review_id(
    db: aiosqlite.Connection,
    review_id: int,
) -> dict | None:
    """通过 review_id 查询分析结果。"""
    cursor = await db.execute(
        "SELECT * FROM analyses WHERE review_id = ?", (review_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def upsert_analysis(
    db: aiosqlite.Connection,
    review_id: int,
    data: dict,
    raw_text: str = "",
    model_used: str = "",
) -> int:
    """
    插入或替换分析结果（按 review_id）。
    返回分析记录的 ID。
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    persona = data.get("customer_persona", {}) or {}
    email = data.get("recovery_email", {}) or {}

    cursor = await db.execute(
        """
        INSERT INTO analyses
            (review_id, reason_category, anger_level,
             communication_style, cultural_traits, suggested_approach,
             email_subject, email_body, email_language,
             raw_llm_output, model_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(review_id) DO UPDATE SET
            reason_category=excluded.reason_category,
            anger_level=excluded.anger_level,
            communication_style=excluded.communication_style,
            cultural_traits=excluded.cultural_traits,
            suggested_approach=excluded.suggested_approach,
            email_subject=excluded.email_subject,
            email_body=excluded.email_body,
            email_language=excluded.email_language,
            raw_llm_output=excluded.raw_llm_output,
            model_used=excluded.model_used
        """,
        (
            review_id,
            data.get("reason_category", "other"),
            data.get("anger_level", 3),
            persona.get("communication_style", ""),
            persona.get("cultural_traits", ""),
            persona.get("suggested_approach", ""),
            email.get("subject", ""),
            email.get("body", ""),
            email.get("language", "en"),
            raw_text,
            model_used,
            now,
        ),
    )
    await db.commit()
    return cursor.lastrowid or review_id


# ============================================================
#  Batch Jobs CRUD
# ============================================================

async def create_batch_job(
    db: aiosqlite.Connection,
    job_type: str = "batch_analysis",
    total_items: int = 0,
) -> int:
    """创建批量任务记录，返回 job_id。"""
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        """
        INSERT INTO batch_jobs (job_type, status, total_items, created_at, updated_at)
        VALUES (?, 'running', ?, ?, ?)
        """,
        (job_type, total_items, now, now),
    )
    await db.commit()
    return cursor.lastrowid


async def update_batch_job(
    db: aiosqlite.Connection,
    job_id: int,
    status: str | None = None,
    completed: int | None = None,
    error_message: str | None = None,
) -> None:
    """更新批量任务状态。只更新传入的非 None 字段。"""
    now = datetime.now(timezone.utc).isoformat()
    sets = ["updated_at = ?"]
    params: list = [now]

    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if completed is not None:
        sets.append("completed_items = ?")
        params.append(completed)
    if error_message is not None:
        sets.append("error_message = ?")
        params.append(error_message)

    params.append(job_id)
    await db.execute(
        f"UPDATE batch_jobs SET {', '.join(sets)} WHERE id = ?",
        params,
    )
    await db.commit()


async def get_batch_jobs(
    db: aiosqlite.Connection,
    limit: int = 20,
) -> list[dict]:
    """获取最近的批量任务列表。"""
    cursor = await db.execute(
        "SELECT * FROM batch_jobs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# ============================================================
#  Webhook CRUD
# ============================================================

async def create_webhook(
    db: aiosqlite.Connection,
    name: str,
    webhook_type: str,
    url: str,
) -> int:
    """创建 webhook 配置，返回 id。"""
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        """
        INSERT INTO webhooks (name, webhook_type, url, is_active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (name, webhook_type, url, now),
    )
    await db.commit()
    return cursor.lastrowid


async def get_active_webhooks(
    db: aiosqlite.Connection,
) -> list[dict]:
    """获取所有激活的 webhook。"""
    cursor = await db.execute(
        "SELECT * FROM webhooks WHERE is_active = 1 ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_webhook(
    db: aiosqlite.Connection,
    webhook_id: int,
) -> None:
    """软删除 webhook（设为非激活）。"""
    await db.execute(
        "UPDATE webhooks SET is_active = 0 WHERE id = ?",
        (webhook_id,),
    )
    await db.commit()


async def log_webhook_delivery(
    db: aiosqlite.Connection,
    webhook_id: int,
    status: str,
    response_code: int = 0,
    error_message: str = "",
) -> None:
    """记录 webhook 发送日志。"""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO webhook_logs (webhook_id, status, response_code, error_message, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (webhook_id, status, response_code, error_message, now),
    )
    await db.commit()


# ============================================================
#  Users CRUD（认证系统）
# ============================================================

async def create_user(
    db: aiosqlite.Connection,
    username: str,
    password: str,
) -> int | None:
    """
    创建新用户。返回用户 ID，如果用户名已存在则返回 None。

    密码使用 SHA-256 哈希存储。
    """
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()

    try:
        cursor = await db.execute(
            """
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, now),
        )
        await db.commit()
        return cursor.lastrowid
    except aiosqlite.IntegrityError:
        logger.warning("用户名已存在: %s", username)
        return None


async def verify_user(
    db: aiosqlite.Connection,
    username: str,
    password: str,
) -> dict | None:
    """
    验证用户凭据。成功返回用户信息字典，失败返回 None。
    """
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    cursor = await db.execute(
        "SELECT id, username FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
        (username, password_hash),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {"id": row["id"], "username": row["username"]}


# ============================================================
#  A/B Variants CRUD
# ============================================================

async def create_ab_variant(
    db: aiosqlite.Connection,
    review_id: int,
    variant_label: str,
    email_subject: str = "",
    email_body: str = "",
) -> int:
    """创建 A/B 邮件变体记录，返回 variant_id。"""
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        """
        INSERT INTO ab_variants (review_id, variant_label, email_subject, email_body, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (review_id, variant_label, email_subject, email_body, now),
    )
    await db.commit()
    return cursor.lastrowid


async def get_variants_for_review(
    db: aiosqlite.Connection,
    review_id: int,
) -> list[dict]:
    """获取指定评论的所有 A/B 变体。"""
    cursor = await db.execute(
        "SELECT * FROM ab_variants WHERE review_id = ? ORDER BY variant_label",
        (review_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def record_ab_event(
    db: aiosqlite.Connection,
    variant_id: int,
    event_type: str,
) -> int:
    """记录 A/B 事件（如 sent, opened, clicked），返回 event_id。"""
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        """
        INSERT INTO ab_events (variant_id, event_type, created_at)
        VALUES (?, ?, ?)
        """,
        (variant_id, event_type, now),
    )
    await db.commit()
    return cursor.lastrowid


async def get_ab_stats(db: aiosqlite.Connection) -> dict:
    """获取 A/B 测试统计摘要。"""
    cursor = await db.execute("SELECT COUNT(*) as total FROM ab_variants")
    row = await cursor.fetchone()
    total_variants = row["total"] if row else 0

    cursor = await db.execute("""
        SELECT variant_label, COUNT(*) as count
        FROM ab_variants GROUP BY variant_label
    """)
    label_rows = await cursor.fetchall()
    by_label = {r["variant_label"]: r["count"] for r in label_rows}

    cursor = await db.execute("""
        SELECT e.event_type, COUNT(*) as count
        FROM ab_events e
        JOIN ab_variants v ON e.variant_id = v.id
        GROUP BY e.event_type
    """)
    event_rows = await cursor.fetchall()
    events = {r["event_type"]: r["count"] for r in event_rows}

    cursor = await db.execute("""
        SELECT v.variant_label, e.event_type, COUNT(*) as count
        FROM ab_events e
        JOIN ab_variants v ON e.variant_id = v.id
        GROUP BY v.variant_label, e.event_type
        ORDER BY v.variant_label, e.event_type
    """)
    detail_rows = await cursor.fetchall()

    variant_stats = {}
    for r in detail_rows:
        label = r["variant_label"]
        if label not in variant_stats:
            variant_stats[label] = {}
        variant_stats[label][r["event_type"]] = r["count"]

    return {
        "total_variants": total_variants,
        "by_label": by_label,
        "events": events,
        "variant_stats": variant_stats,
    }


# ============================================================
#  Analytics Summary
# ============================================================

async def get_analytics_summary(db: aiosqlite.Connection) -> dict:
    """获取分析面板概览统计数据。"""
    cursor = await db.execute("SELECT COUNT(*) as total FROM reviews WHERE is_negative = 1")
    row = await cursor.fetchone()
    total_reviews = row["total"] if row else 0

    cursor = await db.execute("SELECT COUNT(*) as total FROM analyses")
    row = await cursor.fetchone()
    analyzed_reviews = row["total"] if row else 0

    cursor = await db.execute("SELECT ROUND(AVG(anger_level), 1) as avg_anger FROM analyses")
    row = await cursor.fetchone()
    avg_anger = row["avg_anger"] if row and row["avg_anger"] is not None else 0

    cursor = await db.execute("""
        SELECT reason_category, COUNT(*) as count
        FROM analyses GROUP BY reason_category ORDER BY count DESC LIMIT 10
    """)
    reason_rows = await cursor.fetchall()
    top_reasons = [{"category": r["reason_category"], "count": r["count"]} for r in reason_rows]

    return {
        "total_reviews": total_reviews,
        "analyzed_reviews": analyzed_reviews,
        "avg_anger": avg_anger,
        "top_reasons": top_reasons,
    }


async def get_webhook_stats(db: aiosqlite.Connection) -> dict:
    """获取 Webhook 相关统计。"""
    cursor = await db.execute("SELECT COUNT(*) as total FROM webhooks WHERE is_active = 1")
    row = await cursor.fetchone()
    active_webhooks = row["total"] if row else 0

    cursor = await db.execute("""
        SELECT status, COUNT(*) as count
        FROM webhook_logs GROUP BY status ORDER BY count DESC
    """)
    log_rows = await cursor.fetchall()
    log_stats = {r["status"]: r["count"] for r in log_rows}

    cursor = await db.execute("SELECT COUNT(*) as total FROM webhook_logs")
    row = await cursor.fetchone()
    total_deliveries = row["total"] if row else 0

    return {
        "active_webhooks": active_webhooks,
        "total_deliveries": total_deliveries,
        "delivery_stats": log_stats,
    }


async def get_user_by_username(
    db: aiosqlite.Connection,
    username: str,
) -> dict | None:
    """按用户名查询用户，返回完整用户字典或 None。"""
    cursor = await db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None
