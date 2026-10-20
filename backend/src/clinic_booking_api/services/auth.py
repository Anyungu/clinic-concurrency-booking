from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clinic_booking_api.models import AppUser
from clinic_booking_api.utilities.auth import encode_token

TOKEN_LIFETIME = timedelta(minutes=120)
password_hash = PasswordHash.recommended()


async def get_active_user(
    session: AsyncSession,
    condition: ColumnElement[bool],
) -> AppUser | None:
    return (
        await session.exec(
            select(AppUser).where(
                condition,
                col(AppUser.deleted_at).is_(None),
                col(AppUser.is_active).is_(True),
            )
        )
    ).first()


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
    user = await get_active_user(
        session,
        col(AppUser.email) == email.strip().lower(),
    )
    if user is None or not password_hash.verify(password, user.password_hash):
        return None

    return create_access_token(user.id)


def create_access_token(user_id: UUID) -> str:
    return encode_token(
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + TOKEN_LIFETIME,
        }
    )


async def get_current_user(
    session: AsyncSession,
    user_id: UUID,
) -> CurrentUser | None:
    user = await get_active_user(session, col(AppUser.id) == user_id)
    if user is None:
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
