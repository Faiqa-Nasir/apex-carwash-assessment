"""Request and response bodies: the JSON shape of the API.

Pydantic checks every request body and query value here, before any of our
code runs. The examples show up in the Swagger docs at /docs.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field

from app.booking.domain.appointment import AppointmentStatus

# ---- errors ----


class ErrorBody(BaseModel):
    code: str = Field(examples=["overlapping_booking"])
    message: str = Field(examples=["this slot at the branch is already booked"])
    details: list[dict] = Field(default=[], examples=[[]])


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---- pagination ----


class PageInfo(BaseModel):
    total: int = Field(examples=[42])
    limit: int = Field(examples=[20])
    offset: int = Field(examples=[0])


# ---- branches and services ----


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(examples=["Riyadh - Olaya"])
    timezone: str = Field(examples=["Asia/Riyadh"])


class BranchPage(PageInfo):
    items: list[BranchOut]


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(examples=["Exterior Wash"])
    duration_minutes: int = Field(examples=[30])
    price: Decimal = Field(examples=["45.00"])


class ServicePage(PageInfo):
    items: list[ServiceOut]


# ---- customers ----


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Sara Al-Harbi"])
    email: EmailStr = Field(max_length=254, examples=["sara@example.com"])
    phone: str | None = Field(default=None, max_length=30, examples=["+966500000001"])


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str = Field(examples=["Sara Al-Harbi"])
    email: str = Field(examples=["sara@example.com"])
    phone: str | None = Field(examples=["+966500000001"])
    created_at: datetime


class CustomerPage(PageInfo):
    items: list[CustomerOut]


# ---- appointments ----


class AppointmentIn(BaseModel):
    # The examples are seeded ids, so "Try it out" in /docs works as is.
    branch_id: UUID = Field(examples=["00000000-0000-0000-0000-00000000b001"])
    customer_id: UUID = Field(examples=["00000000-0000-0000-0000-00000000c001"])
    service_id: UUID = Field(examples=["00000000-0000-0000-0000-00000000a002"])
    # AwareDatetime rejects times without a timezone, e.g. "2026-10-20T10:00".
    starts_at: AwareDatetime = Field(
        description="Start time with a timezone offset. The end time comes from the service.",
        examples=["2030-01-10T10:00:00+03:00"],
    )


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    branch_id: UUID
    service_id: UUID
    customer_id: UUID
    starts_at: datetime = Field(examples=["2030-01-10T07:00:00Z"])
    ends_at: datetime = Field(examples=["2030-01-10T07:30:00Z"])
    status: AppointmentStatus
    price_at_booking: Decimal = Field(
        description="The service price when booked; later price changes do not affect it.",
        examples=["45.00"],
    )
    created_at: datetime
    updated_at: datetime


class AppointmentPage(PageInfo):
    items: list[AppointmentOut]
