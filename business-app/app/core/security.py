"""安全模块：JWT 签发与校验、密码哈希、当前用户依赖。

- bcrypt 直接做密码哈希
- python-jose 签发与解析 JWT access token
- OAuth2PasswordBearer 提取 token
- get_current_user / get_current_active_user 作为 FastAPI 依赖
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.session import get_session
from ..models.user import User
from ..repositories.user_repository import UserRepository
from ..schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def hash_password(password: str) -> str:
    """密码哈希（bcrypt）。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """签发 JWT access token。

    Args:
        subject: token 主体（用户 email）。
        expires_delta: 自定义过期时长，默认取配置。
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> TokenData:
    """解析 JWT，返回 TokenData。"""
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return TokenData(sub=payload.get("sub"), exp=payload.get("exp"))


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """从 token 解析当前用户，注入到路由。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_token(token)
        if token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    repo = UserRepository(session)
    user = await repo.get_by_email(token_data.sub)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """确保当前用户已激活。"""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已被禁用")
    return current_user
