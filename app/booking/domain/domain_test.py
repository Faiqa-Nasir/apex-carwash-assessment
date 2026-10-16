"""Domain tests: business rules in plain Python, no database needed."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from .appointment import Appointment, AppointmentStatus
from .branch import Branch
from .customer import Customer
from .errors import InvalidStatusTransition, OverlappingBooking, PastBookingTime, ValidationError
from .service import Service

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
TOMORROW = NOW + timedelta(days=1)
BRANCH_A = uuid4()
CAR_WASH = Service(name="Car Wash", duration_minutes=30, price=Decimal("50.00"))
FULL_DETAIL = Service(name="Full Detail", duration_minutes=90, price=Decimal("200.00"))


def book(branch_id, service, starts_at, already_booked=()):
    """Book `service` at `branch_id`, given the appointments already there."""
    return Appointment.book(
        branch_id=branch_id,
        customer_id=uuid4(),
        service=service,
        starts_at=starts_at,
        now=NOW,
        already_booked=already_booked,
    )


# =============================================================================
# Appointment
# =============================================================================


# --- happy paths: booking ----------------------------------------------------


def test_book_takes_price_and_duration_from_the_service():
    appointment = book(BRANCH_A, FULL_DETAIL, TOMORROW)
    assert appointment.status == AppointmentStatus.SCHEDULED
    assert appointment.service_id == FULL_DETAIL.id
    assert appointment.price_at_booking == Decimal("200.00")
    assert appointment.slot.ends_at == TOMORROW + timedelta(minutes=90)


def test_booking_that_starts_when_another_ends_is_allowed():
    first = book(BRANCH_A, CAR_WASH, TOMORROW)  # 12:00-12:30

    # Starts exactly when the first one ends: 12:30-13:00.
    second = book(BRANCH_A, CAR_WASH, TOMORROW + timedelta(minutes=30), already_booked=[first])
    assert second.is_active

    # Other branches and cancelled or completed bookings never reach
    # already_booked: the repository query leaves them out.


def test_start_time_in_another_timezone_is_stored_as_utc():
    riyadh_3pm = datetime(2026, 10, 17, 15, 0, tzinfo=ZoneInfo("Asia/Riyadh"))  # +03:00
    appointment = book(BRANCH_A, CAR_WASH, riyadh_3pm)
    assert appointment.slot.starts_at == TOMORROW  # 12:00 UTC
    assert appointment.slot.starts_at.tzinfo == UTC


# --- happy paths: status -----------------------------------------------------


def test_cancel_sets_status_and_updated_at():
    appointment = book(BRANCH_A, CAR_WASH, TOMORROW)
    appointment.cancel(NOW)
    assert appointment.status == AppointmentStatus.CANCELLED
    assert appointment.updated_at == NOW
    assert not appointment.is_active


def test_complete_sets_status():
    appointment = book(BRANCH_A, CAR_WASH, TOMORROW)
    appointment.complete(NOW)
    assert appointment.status == AppointmentStatus.COMPLETED


# --- unhappy paths -----------------------------------------------------------


def test_rejects_past_and_overlapping_bookings():
    # The start time has already passed.
    with pytest.raises(PastBookingTime, match="starts_at must be in the future"):
        book(BRANCH_A, CAR_WASH, NOW - timedelta(minutes=1))

    booking_a = book(BRANCH_A, FULL_DETAIL, TOMORROW)  # 12:00-13:30

    # Starts while booking A is still running: 12:30-13:00.
    message = "this slot at the branch is already booked from 2026-10-17T12:00:00Z to 2026-10-17T13:30:00Z"
    with pytest.raises(OverlappingBooking, match=message):
        book(BRANCH_A, CAR_WASH, TOMORROW + timedelta(minutes=30), already_booked=[booking_a])


def test_rejects_start_time_without_timezone():
    # 12:00 with no timezone could mean any of 24 different moments.
    with pytest.raises(ValidationError, match="timezone"):
        book(BRANCH_A, CAR_WASH, datetime(2026, 10, 17, 12, 0))


def test_finished_appointment_cannot_change_again():
    cancelled = book(BRANCH_A, CAR_WASH, TOMORROW)
    cancelled.cancel(NOW)
    with pytest.raises(InvalidStatusTransition, match="already cancelled"):
        cancelled.cancel(NOW)
    with pytest.raises(InvalidStatusTransition, match="already cancelled"):
        cancelled.complete(NOW)

    completed = book(BRANCH_A, CAR_WASH, TOMORROW)
    completed.complete(NOW)
    with pytest.raises(InvalidStatusTransition, match="already completed"):
        completed.cancel(NOW)
    with pytest.raises(InvalidStatusTransition, match="already completed"):
        completed.complete(NOW)


# =============================================================================
# Branch, Service and Customer
# =============================================================================


# --- happy paths -------------------------------------------------------------


def test_branch_is_created_with_its_own_timezone():
    riyadh = Branch(name="Riyadh North", timezone="Asia/Riyadh")
    dubai = Branch(name="Dubai Marina", timezone="Asia/Dubai")

    assert riyadh.timezone == "Asia/Riyadh"
    assert dubai.timezone == "Asia/Dubai"
    assert riyadh.id != dubai.id  # each branch gets its own id


def test_service_is_created_with_its_duration_and_price():
    car_wash = Service(name="Car Wash", duration_minutes=30, price=Decimal("50.00"))
    assert car_wash.duration_minutes == 30
    assert car_wash.price == Decimal("50.00")

    # A price of zero is allowed.
    vacuum = Service(name="Vacuum", duration_minutes=10, price=Decimal("0"))
    assert vacuum.price == Decimal("0")


def test_customer_name_email_and_phone_are_cleaned_up():
    # Name is trimmed, email is trimmed and lowercased, phone is trimmed.
    sara = Customer(name="  Sara Khan ", email="  Sara.Khan@Example.COM ", phone=" +966500000001 ")
    assert sara.name == "Sara Khan"
    assert sara.email == "sara.khan@example.com"
    assert sara.phone == "+966500000001"

    # Phone is optional, and a blank phone counts as no phone.
    no_phone = Customer(name="Omar", email="omar@example.com")
    blank_phone = Customer(name="Lina", email="lina@example.com", phone="   ")
    assert no_phone.phone is None
    assert blank_phone.phone is None


# --- unhappy paths -----------------------------------------------------------


def test_branch_rejects_missing_or_unknown_timezone_and_blank_name():
    # No timezone at all: there is no shared default.
    with pytest.raises(TypeError):
        Branch(name="No Zone")

    # A timezone name that does not exist.
    with pytest.raises(ValidationError, match="unknown timezone"):
        Branch(name="Mars", timezone="Mars/Olympus")

    # A blank name.
    with pytest.raises(ValidationError, match="name"):
        Branch(name="   ", timezone="Asia/Riyadh")


def test_service_rejects_bad_duration_price_or_name():
    # Duration must be at least one minute.
    with pytest.raises(ValidationError, match="duration"):
        Service(name="Wax", duration_minutes=0, price=Decimal("10"))
    with pytest.raises(ValidationError, match="duration"):
        Service(name="Wax", duration_minutes=-10, price=Decimal("10"))

    # Price cannot be negative.
    with pytest.raises(ValidationError, match="price"):
        Service(name="Wax", duration_minutes=10, price=Decimal("-1"))

    # Name cannot be blank.
    with pytest.raises(ValidationError, match="name"):
        Service(name="", duration_minutes=10, price=Decimal("10"))


def test_customer_rejects_blank_name_or_email():
    with pytest.raises(ValidationError, match="name"):
        Customer(name="   ", email="sara@example.com")

    with pytest.raises(ValidationError, match="email"):
        Customer(name="Sara", email="   ")
