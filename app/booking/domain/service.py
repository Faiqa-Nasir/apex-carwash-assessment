"""Service: something the operator sells. Seeded, read-only through the API.

One shared catalog: every branch offers every service at the same price.
A branch and a service are only linked through an appointment.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from .errors import ValidationError


@dataclass(frozen=True)
class Service:
    name: str
    duration_minutes: int
    price: Decimal
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("service name is required")
        if self.duration_minutes <= 0:
            raise ValidationError("duration_minutes must be positive")
        if self.price < 0:
            raise ValidationError("price must not be negative")
