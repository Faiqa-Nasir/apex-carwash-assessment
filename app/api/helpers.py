"""FastAPI dependencies: a UnitOfWork per request, and bearer-token auth for writes."""

import secrets

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.errors import Unauthorized
from app.booking.services.unit_of_work import UnitOfWork
from app.config import Settings, get_settings

# auto_error=False so a missing token goes through our own 401 error format.
bearer = HTTPBearer(auto_error=False)


def get_uow(settings: Settings = Depends(get_settings)) -> UnitOfWork:
    return UnitOfWork(settings.database_url)


def require_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    """Reject the request unless it sends 'Authorization: Bearer <API_TOKEN>'."""
    if credentials is None:
        raise Unauthorized()
    # compare_digest takes the same time whether the first or last character
    # is wrong, so the token cannot be guessed by timing responses.
    if not secrets.compare_digest(credentials.credentials, settings.api_token):
        raise Unauthorized()
