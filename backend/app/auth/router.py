from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.security import hash_password, verify_password
from app.core.config import Settings, get_settings
from app.db.models.user import User
from app.db.session import get_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=8, max_length=1024)


def _to_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), email=user.email, display_name=user.display_name)


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    request.session["user_id"] = str(user.id)
    return _to_out(user)


@router.post("/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"logged_out": True}


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return _to_out(current)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    if not verify_password(body.current_password, current.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_current_password")
    current.password_hash = hash_password(body.new_password)
    await session.commit()
    return {"changed": True}
