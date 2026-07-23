"""
JWT 认证系统

提供用户注册、登录、JWT 令牌签发与验证功能。
"""
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.database import create_user, get_connection, verify_user

# ============================================================
#  配置
# ============================================================

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# ============================================================
#  Pydantic 模型
# ============================================================


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# ============================================================
#  JWT 工具函数
# ============================================================

def create_access_token(username: str) -> str:
    """生成 24 小时过期的 JWT 令牌。"""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """验证 JWT 令牌，成功返回 payload，失败返回 None。"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ============================================================
#  FastAPI 依赖
# ============================================================

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI 依赖函数：从 Authorization Bearer 头提取 token 并验证。
    返回 payload（包含 sub 字段即 username）。
    未认证时抛出 401。
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")

    return payload


# ============================================================
#  API 路由
# ============================================================

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=AuthResponse)
async def register(body: AuthRequest, db=Depends(get_connection)):
    """注册新用户。"""
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(body.password) < 4:
        raise HTTPException(status_code=400, detail="密码长度至少 4 位")

    user_id = await create_user(db, body.username, body.password)
    if user_id is None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    token = create_access_token(body.username)
    return AuthResponse(
        access_token=token,
        username=body.username,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest, db=Depends(get_connection)):
    """用户登录，返回 JWT 令牌。"""
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = await verify_user(db, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(body.username)
    return AuthResponse(
        access_token=token,
        username=body.username,
    )


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息（需要认证）。"""
    return {"username": current_user.get("sub", "unknown")}
