"""安全模块：JWT 签发与校验、密码哈希。

阶段 8.3 实现：
- OAuth2 Password Flow
- JWT access token 签发与解析
- passlib bcrypt 密码哈希
- Depends(get_current_user) 注入当前用户
"""

from __future__ import annotations


def hash_password(password: str) -> str:
    """密码哈希。阶段 8.3 实现。"""
    raise NotImplementedError


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码。阶段 8.3 实现。"""
    raise NotImplementedError


def create_access_token(subject: str) -> str:
    """签发 JWT。阶段 8.3 实现。"""
    raise NotImplementedError


def decode_token(token: str) -> dict:
    """解析 JWT。阶段 8.3 实现。"""
    raise NotImplementedError