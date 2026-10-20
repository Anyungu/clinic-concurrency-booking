from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clinic_booking_api.auth import (
    LoginRequest,
    TokenResponse,
    create_access_token,
    password_hash,
)
from clinic_booking_api.db import get_session
from clinic_booking_api.models import AppUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    user = (
        await session.exec(
            select(AppUser).where(
                AppUser.email == credentials.email.strip().lower(),
                col(AppUser.deleted_at).is_(None),
            )
        )
    ).first()
    if (
        user is None
        or not user.is_active
        or not password_hash.verify(credentials.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
    )
