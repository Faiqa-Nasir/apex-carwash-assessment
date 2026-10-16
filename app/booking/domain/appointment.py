"""Appointment: a customer booking a service at a branch for a time slot."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from .errors import InvalidStatusTransition, OverlappingBooking, PastBookingTime
from .service import Service
from .time_slot import TimeSlot


class AppointmentStatus(StrEnum):
    """SCHEDULED is the only live state; COMPLETED and CANCELLED are final."""

    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class Appointment:
    branch_id: UUID
    service_id: UUID
    customer_id: UUID
    slot: TimeSlot
    price_at_booking: Decimal  # snapshot: the catalog price may change later
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def book(
        cls,
        *,
        branch_id: UUID,
        customer_id: UUID,
        service: Service,
        starts_at: datetime,
        now: datetime,
        already_booked: Iterable["Appointment"],
    ) -> "Appointment":
        """Create a new booking. Rejects past times and slots that clash with another booking.

        already_booked is the scheduled appointments at this branch around the
        new slot; the repository picks them with the same overlap rule.
        """
        slot = TimeSlot.from_start(starts_at, service.duration_minutes)
        if slot.is_in_past(now):
            raise PastBookingTime()
        for booked in already_booked:
            if booked.slot.overlaps(slot):
                raise OverlappingBooking(
                    f"this slot at the branch is already booked from {to_text(booked.starts_at)}"
                    f" to {to_text(booked.ends_at)}"
                )
        return cls(branch_id, service.id, customer_id, slot, service.price)

    @property
    def starts_at(self) -> datetime:
        return self.slot.starts_at

    @property
    def ends_at(self) -> datetime:
        return self.slot.ends_at

    @property
    def is_active(self) -> bool:
        return self.status == AppointmentStatus.SCHEDULED

    def cancel(self, now: datetime) -> None:
        self._change_status(AppointmentStatus.CANCELLED, now)

    def complete(self, now: datetime) -> None:
        self._change_status(AppointmentStatus.COMPLETED, now)

    def _change_status(self, target: AppointmentStatus, now: datetime) -> None:
        """Only a SCHEDULED appointment can change; the others are final."""
        if self.status != AppointmentStatus.SCHEDULED:
            raise InvalidStatusTransition(f"appointment is already {self.status.lower()}")
        self.status = target
        self.updated_at = now


def to_text(value: datetime) -> str:
    """A UTC time as the API writes it, e.g. 2026-10-20T07:00:00Z."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
