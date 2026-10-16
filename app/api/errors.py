"""One place where errors become HTTP responses.

Every error, including FastAPI's own 422 and 404 responses, uses one shape:
    {"error": {"code": "...", "message": "...", "details": [...]}}
Unexpected errors are logged on the server and the client gets a generic
500, so stack traces and internals never leave the server.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.schemas import ErrorResponse
from app.booking.domain.errors import (
    BookingError,
    ConflictError,
    DuplicateEmail,
    InvalidStatusTransition,
    NotFound,
    OverlappingBooking,
    PastBookingTime,
    ValidationError,
)

logger = logging.getLogger(__name__)


class Unauthorized(Exception):
    """The bearer token is missing or wrong."""


# A stable code per error, so clients can branch on it instead of the message.
ERROR_CODES = {
    ValidationError: "validation_error",
    PastBookingTime: "past_booking_time",
    OverlappingBooking: "overlapping_booking",
    DuplicateEmail: "duplicate_email",
    InvalidStatusTransition: "invalid_status_transition",
    NotFound: "not_found",
}


def error_response(
    status_code: int, code: str, message: str, details: list | None = None, headers=None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
        headers=headers,
    )


def handle_booking_error(request: Request, exc: BookingError) -> JSONResponse:
    """Domain errors: 404 not found, 409 conflict, 400 broken business rule."""
    if isinstance(exc, NotFound):
        status_code = 404
    elif isinstance(exc, ConflictError):
        status_code = 409
    else:
        status_code = 400
    code = ERROR_CODES.get(type(exc), "bad_request")
    return error_response(status_code, code, str(exc))


def handle_unauthorized(request: Request, exc: Unauthorized) -> JSONResponse:
    return error_response(
        401,
        "unauthorized",
        "a valid bearer token is required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's 422 (wrong type, missing field, bad format) in our error shape.

    Only the field and the message are returned, never the submitted value.
    """
    details = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"])
        details.append({"field": field, "message": error["msg"]})
    return error_response(422, "invalid_request", "the request is invalid", details)


def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    """FastAPI's own HTTP errors, such as 404 for an unknown URL."""
    code = "not_found" if exc.status_code == 404 else "http_error"
    return error_response(exc.status_code, code, str(exc.detail))


def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unexpected error on %s %s", request.method, request.url.path, exc_info=exc)
    return error_response(500, "internal_error", "an unexpected error occurred")


def add_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BookingError, handle_booking_error)
    app.add_exception_handler(Unauthorized, handle_unauthorized)
    app.add_exception_handler(RequestValidationError, handle_request_validation)
    app.add_exception_handler(HTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)


def error_responses(*status_codes: int) -> dict:
    """The error responses a route can return, for the OpenAPI docs."""
    responses = {}
    for status_code in status_codes:
        responses[status_code] = {"model": ErrorResponse}
    return responses
