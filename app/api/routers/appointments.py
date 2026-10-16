"""Booking, listing, reading, cancelling and completing appointments.

Thin: check auth, let Pydantic parse the input, call one command or query,
shape the response. Every endpoint needs the token.
"""

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.errors import error_responses
from app.api.helpers import get_uow, require_token
from app.api.schemas import AppointmentIn, AppointmentOut, AppointmentPage
from app.booking.domain.appointment import AppointmentStatus
from app.booking.services import commands, queries
from app.booking.services.unit_of_work import UnitOfWork

router = APIRouter(tags=["appointments"], dependencies=[Depends(require_token)])


@router.post(
    "/appointments",
    status_code=201,
    responses=error_responses(400, 401, 404, 409, 422),
)
def book_appointment(body: AppointmentIn, uow: UnitOfWork = Depends(get_uow)) -> AppointmentOut:
    """Book a service at a branch.

    The end time is the start plus the service duration, and the price is
    copied from the service. Fails with 400 if the start is in the past, 404 if
    the branch, customer or service does not exist, and 409 if the slot at the
    branch is already booked for any part of the time (the message names the clash).
    A slot that starts exactly when another ends is allowed.
    """
    appointment = commands.book_appointment(
        uow,
        branch_id=body.branch_id,
        customer_id=body.customer_id,
        service_id=body.service_id,
        starts_at=body.starts_at,
        now=datetime.now(UTC),
    )
    return AppointmentOut.model_validate(appointment)


@router.get("/appointments", responses=error_responses(401, 422))
def list_appointments(
    branch_id: UUID | None = None,
    status: AppointmentStatus | None = None,
    on_date: date | None = Query(None, alias="date", description="Day in the branch timezone"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> AppointmentPage:
    """All appointments, ordered by start time. Filters are optional and combine.

    An unknown branch_id just gives an empty list; use
    /branches/{branch_id}/appointments to get a 404 instead.
    """
    page = queries.list_appointments(uow, limit, offset, branch_id, status, on_date)
    return AppointmentPage(items=page.items, total=page.total, limit=limit, offset=offset)


@router.get("/branches/{branch_id}/appointments", responses=error_responses(401, 404, 422))
def list_branch_appointments(
    branch_id: UUID,
    status: AppointmentStatus | None = None,
    on_date: date | None = Query(None, alias="date", description="Day in the branch timezone"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> AppointmentPage:
    """One branch's appointments, ordered by start time. 404 if the branch does not exist."""
    page = queries.list_branch_appointments(uow, branch_id, limit, offset, status, on_date)
    return AppointmentPage(items=page.items, total=page.total, limit=limit, offset=offset)


@router.get("/appointments/{appointment_id}", responses=error_responses(401, 404, 422))
def get_appointment(appointment_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> AppointmentOut:
    """One appointment by id."""
    return AppointmentOut.model_validate(queries.get_appointment(uow, appointment_id))


@router.post(
    "/appointments/{appointment_id}/cancel",
    responses=error_responses(401, 404, 409, 422),
)
def cancel_appointment(appointment_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> AppointmentOut:
    """Cancel a scheduled appointment; its slot becomes free again.

    409 if it is already cancelled or completed.
    """
    appointment = commands.cancel_appointment(uow, appointment_id, now=datetime.now(UTC))
    return AppointmentOut.model_validate(appointment)


@router.post(
    "/appointments/{appointment_id}/complete",
    responses=error_responses(401, 404, 409, 422),
)
def complete_appointment(
    appointment_id: UUID, uow: UnitOfWork = Depends(get_uow)
) -> AppointmentOut:
    """Mark a scheduled appointment as done.

    409 if it is already cancelled or completed.
    """
    appointment = commands.complete_appointment(uow, appointment_id, now=datetime.now(UTC))
    return AppointmentOut.model_validate(appointment)
