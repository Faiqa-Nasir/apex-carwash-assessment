"""TimeSlot: the interval an appointment occupies."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .errors import ValidationError


def require_timezone(value: datetime) -> None:
    """Raise an error if the datetime has no timezone."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("datetime must include a timezone offset")


def as_utc(value: datetime) -> datetime:
    """Check the datetime has a timezone, then convert it to UTC."""
    require_timezone(value)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class TimeSlot:
    """Half-open interval [starts_at, ends_at), both timezone-aware.

    Half-open means a slot ending at 10:30 does not clash with one starting
    at 10:30.
    """

    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        require_timezone(self.starts_at)
        require_timezone(self.ends_at)
        if self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be after starts_at")

    @classmethod
    def from_start(cls, starts_at: datetime, duration_minutes: int) -> "TimeSlot":
        starts_at = as_utc(starts_at)
        return cls(starts_at, starts_at + timedelta(minutes=duration_minutes))

    def overlaps(self, other: "TimeSlot") -> bool:
        return self.starts_at < other.ends_at and other.starts_at < self.ends_at

    def is_in_past(self, now: datetime) -> bool:
        return self.starts_at < now
