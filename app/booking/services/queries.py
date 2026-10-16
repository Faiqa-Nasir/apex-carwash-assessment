"""Read use cases: the lists and lookups behind the GET endpoints.

Reads change nothing, so there are no business rules to apply. Each one
opens a transaction, asks a repository, and returns domain objects. The list
queries return a Page: one page of items, plus the total number of matches.
All SQL lives in repositories.py.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.booking.domain.appointment import Appointment, AppointmentStatus
from app.booking.domain.customer import Customer
from app.booking.domain.errors import NotFound
from app.booking.services.unit_of_work import UnitOfWork


@dataclass
class Page:
    items: list
    total: int


def list_branches(uow: UnitOfWork, limit: int, offset: int) -> Page:
    with uow:
        branches = uow.branches.list_page(limit, offset)
        total_branches = uow.branches.count()
    return Page(items=branches, total=total_branches)


def list_services(uow: UnitOfWork, limit: int, offset: int) -> Page:
    with uow:
        services = uow.services.list_page(limit, offset)
        total_services = uow.services.count()
    return Page(items=services, total=total_services)


def list_customers(uow: UnitOfWork, limit: int, offset: int) -> Page:
    with uow:
        customers = uow.customers.list_page(limit, offset)
        total_customers = uow.customers.count()
    return Page(items=customers, total=total_customers)


def list_appointments(
    uow: UnitOfWork,
    limit: int,
    offset: int,
    branch_id: UUID | None = None,
    status: AppointmentStatus | None = None,
    on_date: date | None = None,
) -> Page:
    """Filters are optional and combine with AND. An unknown branch_id gives an empty page."""
    with uow:
        appointments = uow.appointments.list_page(limit, offset, branch_id, status, on_date)
        total_appointments = uow.appointments.count(branch_id, status, on_date)
    return Page(items=appointments, total=total_appointments)


def list_branch_appointments(
    uow: UnitOfWork,
    branch_id: UUID,
    limit: int,
    offset: int,
    status: AppointmentStatus | None = None,
    on_date: date | None = None,
) -> Page:
    """Appointments at one branch. Raises NotFound if the branch does not exist."""
    with uow:
        if uow.branches.get(branch_id) is None:
            raise NotFound("branch not found")
        appointments = uow.appointments.list_page(limit, offset, branch_id, status, on_date)
        total_appointments = uow.appointments.count(branch_id, status, on_date)
    return Page(items=appointments, total=total_appointments)


def get_customer(uow: UnitOfWork, customer_id: UUID) -> Customer:
    with uow:
        customer = uow.customers.get(customer_id)
    if customer is None:
        raise NotFound("customer not found")
    return customer


def get_appointment(uow: UnitOfWork, appointment_id: UUID) -> Appointment:
    with uow:
        appointment = uow.appointments.get(appointment_id)
    if appointment is None:
        raise NotFound("appointment not found")
    return appointment
