"""Customer: belongs to the operator, not a branch; may book anywhere."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from .errors import ValidationError


@dataclass
class Customer:
    name: str
    email: str  # normalised to lowercase; uniqueness is a DB constraint
    phone: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.email = self.email.strip().lower()
        if self.phone is not None:
            self.phone = self.phone.strip() or None
        if not self.name:
            raise ValidationError("name is required")
        if not self.email:
            raise ValidationError("email is required")
