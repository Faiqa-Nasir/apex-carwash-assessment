"""Every error the business can raise."""


class BookingError(Exception):
    """Base for all domain errors."""

    message = "booking error"

    def __init__(self, message=None):
        super().__init__(message or self.message)


class ValidationError(BookingError):
    """Well-formed request that breaks a business rule. -> 400"""


class PastBookingTime(ValidationError):
    message = "starts_at must be in the future"


class ConflictError(BookingError):
    """Request collides with existing state. -> 409"""


class OverlappingBooking(ConflictError):
    message = "this slot at the branch is already booked"


class DuplicateEmail(ConflictError):
    message = "a customer with this email already exists"


class InvalidStatusTransition(ConflictError):
    message = "only a scheduled appointment can be cancelled or completed"


class NotFound(BookingError):
    """The referenced entity does not exist. -> 404"""

    message = "not found"
