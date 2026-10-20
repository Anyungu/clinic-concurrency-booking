from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from clinic_booking_api.config import settings
from clinic_booking_api.db import get_session
from clinic_booking_api.models import AppUser

TOKEN_LIFETIME = timedelta(minutes=120)
password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class CurrentUser(BaseModel):
    user_id: UUID
    role: Literal["patient", "doctor", "staff"]
    patient_id: UUID | None = None
    doctor_id: UUID | None = None


def create_access_token(user_id: UUID) -> str:
    return jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        {
            "sub": str(user_id),
            "exp": datetime.now(UTC) + TOKEN_LIFETIME,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or expired bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentUser:
    if credentials is None:
        raise unauthorized()

    try:
        claims = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
            credentials.credentials,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        subject = claims.get("sub")
        if not isinstance(subject, str):
            raise unauthorized()
        user_id = UUID(subject)
    except InvalidTokenError, TypeError, ValueError:
        raise unauthorized() from None

    user = (
        await session.exec(
            select(AppUser).where(
                AppUser.id == user_id,
                col(AppUser.deleted_at).is_(None),
            )
        )
    ).first()
    if user is None or not user.is_active:
        raise unauthorized()

    if user.role == "patient" and user.patient_id is not None:
        return CurrentUser(
            user_id=user.id,
            role="patient",
            patient_id=user.patient_id,
        )
    if user.role == "doctor" and user.doctor_id is not None:
        return CurrentUser(
            user_id=user.id,
            role="doctor",
            doctor_id=user.doctor_id,
        )
    if user.role == "staff":
        return CurrentUser(user_id=user.id, role="staff")

    raise unauthorized()


CurrentUserDependency = Annotated[CurrentUser, Depends(get_current_user)]
