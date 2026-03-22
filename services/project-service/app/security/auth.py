"""JWT authentication helpers for project-service."""
from __future__ import annotations

from dataclasses import dataclass
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class CurrentUser:
    """Authenticated user extracted from JWT."""

    id: uuid.UUID
    email: str | None = None


def _unauthorized(detail: str = "Invalid or missing credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> CurrentUser:
    """Decode and validate an access token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise _unauthorized("Token validation failed") from exc

    if payload.get("token_type", "access") != "access":
        raise _unauthorized("Invalid token type")

    raw_sub = payload.get("sub")
    if not raw_sub:
        raise _unauthorized("Token subject missing")

    try:
        user_id = uuid.UUID(str(raw_sub))
    except ValueError as exc:
        raise _unauthorized("Token subject is invalid") from exc

    return CurrentUser(id=user_id, email=payload.get("email"))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Resolve current user from bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Missing bearer token")
    return decode_access_token(credentials.credentials)

