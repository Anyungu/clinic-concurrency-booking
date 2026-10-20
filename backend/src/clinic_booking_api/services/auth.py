from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clinic_booking_api.config import settings
from clinic_booking_api.models import AppUser

TOKEN_LIFETIME = timedelta(minutes=120)
password_hash = PasswordHash.recommended()


class CurrentUser(BaseModel):
    user_id: UUID
    role: Literal["patient", "doctor", "staff"]
    patient_id: UUID | None = None
    doctor_id: UUID | None = None


async def authenticate_and_create_token(
    session: AsyncSession,
    email: str,
    password: str,
) -> str | None:
    user = (
        await session.exec(
            select(AppUser).where(
                AppUser.email == email.strip().lower(),
                col(AppUser.deleted_at).is_(None),
            )
        )
    ).first()
    if (
        user is None
        or not user.is_active
        or not password_hash.verify(password, user.password_hash)
    ):
        return None

    return create_access_token(user.id)


def create_access_token(user_id: UUID) -> str:
    return jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + TOKEN_LIFETIME,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )


async def get_current_user(
    session: AsyncSession,
    user_id: UUID,
) -> CurrentUser | None:
    user = (
        await session.exec(
            select(AppUser).where(
                AppUser.id == user_id,
                col(AppUser.deleted_at).is_(None),
            )
        )
    ).first()
    if user is None or not user.is_active:
        return None

    if (
        user.role == "patient"
        and user.patient_id is not None
        and user.doctor_id is None
    ):
        return CurrentUser(
            user_id=user.id,
            role="patient",
            patient_id=user.patient_id,
        )
    if user.role == "doctor" and user.doctor_id is not None and user.patient_id is None:
        return CurrentUser(
            user_id=user.id,
            role="doctor",
            doctor_id=user.doctor_id,
        )
    if user.role == "staff" and user.patient_id is None and user.doctor_id is None:
        return CurrentUser(user_id=user.id, role="staff")

    return None
