from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from clinic_booking_api.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or expired bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_authenticated_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> UUID:
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
        return UUID(subject)
    except InvalidTokenError, TypeError, ValueError:
        raise unauthorized() from None


AuthenticatedUserId = Annotated[UUID, Depends(get_authenticated_user_id)]
