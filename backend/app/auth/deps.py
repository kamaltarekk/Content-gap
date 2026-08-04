"""Authentication dependencies.

Two modes (spec §3.1): ``session`` uses a signed HttpOnly cookie; ``none`` is local no-auth
development that auto-provisions a single dev administrator. MVP has one active administrator but
the user id is never hard-coded.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.core.config import Settings, get_settings
from app.db.models.user import User
from app.db.session import get_session

DEV_ADMIN_EMAIL = "admin@local.dev"


async def _get_or_create_dev_admin(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == DEV_ADMIN_EMAIL))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=DEV_ADMIN_EMAIL, password_hash=hash_password("dev"), display_name="Local Admin")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if settings.auth_mode == "none":
        return await _get_or_create_dev_admin(session)

    raw = request.session.get("user_id")
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    try:
        user_id = uuid.UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated") from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return user
