"""Write use cases.

Each command is one transaction: load what it needs, let the domain apply
the business rules, save. No HTTP and no SQL here.

Commands take a UnitOfWork that has not been opened yet; the API passes one
for the real database, tests pass one for the test database.
"""

from datetime import datetime
from uuid import UUID

from app.booking.domain.appointment import Appointment
from app.booking.domain.customer import Customer
from app.booking.domain.errors import NotFound
from app.booking.domain.time_slot import TimeSlot
from app.booking.services.unit_of_work import UnitOfWork


def create_customer(uow: UnitOfWork, name: str, email: str, phone: str | None = None) -> Customer:
    """Raises DuplicateEmail if another customer already uses the email."""
    customer = Customer(name=name, email=email, phone=phone)
    with uow:
        uow.customers.add(customer)
    return customer


def book_appointment(
    uow: UnitOfWork,
    branch_id: UUID,
    customer_id: UUID,
    service_id: UUID,
    starts_at: datetime,
    now: datetime,
) -> Appointment:
    """Raises NotFound, PastBookingTime or OverlappingBooking.

    An unknown branch, customer or service id in the body is a 404, the same
    as an unknown id in the URL, so the client gets one rule for missing ids.
    """
    with uow:
        if uow.branches.get(branch_id) is None:
            raise NotFound("branch not found")
        if uow.customers.get(customer_id) is None:
            raise NotFound("customer not found")
        service = uow.services.get(service_id)
        if service is None:
            raise NotFound("service not found")

        slot = TimeSlot.from_start(starts_at, service.duration_minutes)
        appointment = Appointment.book(
            branch_id=branch_id,
            customer_id=customer_id,
            service=service,
            starts_at=starts_at,
            now=now,
            already_booked=uow.appointments.list_overlapping(branch_id, slot),
        )
        uow.appointments.add(appointment)
    return appointment


def cancel_appointment(uow: UnitOfWork, appointment_id: UUID, now: datetime) -> Appointment:
    """Raises NotFound, or InvalidStatusTransition if it is already finished."""
    with uow:
        appointment = uow.appointments.get_for_update(appointment_id)
        if appointment is None:
            raise NotFound("appointment not found")
        appointment.cancel(now)
        uow.appointments.save(appointment)
    return appointment


def complete_appointment(uow: UnitOfWork, appointment_id: UUID, now: datetime) -> Appointment:
    """Raises NotFound, or InvalidStatusTransition if it is already finished."""
    with uow:
        appointment = uow.appointments.get_for_update(appointment_id)
        if appointment is None:
            raise NotFound("appointment not found")
        appointment.complete(now)
        uow.appointments.save(appointment)
    return appointment
