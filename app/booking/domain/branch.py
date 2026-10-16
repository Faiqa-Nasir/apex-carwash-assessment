"""Branch: a car wash location that takes one appointment at a time. Seeded, read-only."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .errors import ValidationError


@dataclass(frozen=True)
class Branch:
    name: str
    timezone: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("branch name is required")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValidationError(f"unknown timezone: {self.timezone!r}") from None
