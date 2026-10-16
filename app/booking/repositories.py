"""Repositories: the only code that talks to the database.

One class per table. Every value is passed as a named placeholder
(%(name)s), never formatted into the SQL text, so user input cannot change
a query. Constraint violations that back a business rule are turned into
the matching domain error.
"""

from datetime import date
from uuid import UUID

from psycopg import Connection
from psycopg.errors import ExclusionViolation, UniqueViolation

from app.booking.domain.appointment import Appointment, AppointmentStatus
from app.booking.domain.branch import Branch
from app.booking.domain.customer import Customer
from app.booking.domain.errors import DuplicateEmail, OverlappingBooking
from app.booking.domain.service import Service
from app.booking.domain.time_slot import TimeSlot


class BranchRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def get(self, id: UUID) -> Branch | None:
        row = self.conn.execute(
            "SELECT id, name, timezone FROM branches WHERE id = %(id)s",
            {"id": id},
        ).fetchone()
        return Branch(**row) if row else None

    def list_page(self, limit: int, offset: int) -> list[Branch]:
        rows = self.conn.execute(
            """
            SELECT id, name, timezone
            FROM branches
            ORDER BY name, id
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"limit": limit, "offset": offset},
        ).fetchall()
        return [Branch(**row) for row in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT count(*) AS total FROM branches").fetchone()["total"]


class ServiceRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def get(self, id: UUID) -> Service | None:
        row = self.conn.execute(
            "SELECT id, name, duration_minutes, price FROM services WHERE id = %(id)s",
            {"id": id},
        ).fetchone()
        return Service(**row) if row else None

    def list_page(self, limit: int, offset: int) -> list[Service]:
        rows = self.conn.execute(
            """
            SELECT id, name, duration_minutes, price
            FROM services
            ORDER BY name, id
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"limit": limit, "offset": offset},
        ).fetchall()
        return [Service(**row) for row in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT count(*) AS total FROM services").fetchone()["total"]


class CustomerRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def add(self, customer: Customer) -> None:
        """Store a new customer. Raises DuplicateEmail if the email is taken."""
        try:
            row = self.conn.execute(
                """
                INSERT INTO customers (id, name, email, phone)
                VALUES (%(id)s, %(name)s, %(email)s, %(phone)s)
                RETURNING created_at
                """,
                {
                    "id": customer.id,
                    "name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone,
                },
            ).fetchone()
        except UniqueViolation as exc:
            if exc.diag.constraint_name == "uq_customers_email":
                raise DuplicateEmail() from None
            raise
        customer.created_at = row["created_at"]

    def get(self, id: UUID) -> Customer | None:
        row = self.conn.execute(
            "SELECT id, name, email, phone, created_at FROM customers WHERE id = %(id)s",
            {"id": id},
        ).fetchone()
        return Customer(**row) if row else None

    def list_page(self, limit: int, offset: int) -> list[Customer]:
        rows = self.conn.execute(
            """
            SELECT id, name, email, phone, created_at
            FROM customers
            ORDER BY created_at, id
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"limit": limit, "offset": offset},
        ).fetchall()
        return [Customer(**row) for row in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT count(*) AS total FROM customers").fetchone()["total"]


class AppointmentRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def add(self, appointment: Appointment) -> None:
        """Store a new appointment. Raises OverlappingBooking if the slot at the branch is taken."""
        try:
            row = self.conn.execute(
                """
                INSERT INTO appointments
                    (id, branch_id, service_id, customer_id,
                     starts_at, ends_at, status, price_at_booking)
                VALUES
                    (%(id)s, %(branch_id)s, %(service_id)s, %(customer_id)s,
                     %(starts_at)s, %(ends_at)s, %(status)s, %(price_at_booking)s)
                RETURNING created_at, updated_at
                """,
                {
                    "id": appointment.id,
                    "branch_id": appointment.branch_id,
                    "service_id": appointment.service_id,
                    "customer_id": appointment.customer_id,
                    "starts_at": appointment.slot.starts_at,
                    "ends_at": appointment.slot.ends_at,
                    "status": appointment.status.value,
                    "price_at_booking": appointment.price_at_booking,
                },
            ).fetchone()
        except ExclusionViolation:
            # Another request booked an overlapping slot after our check ran.
            raise OverlappingBooking() from None
        appointment.created_at = row["created_at"]
        appointment.updated_at = row["updated_at"]

    def get(self, id: UUID) -> Appointment | None:
        row = self.conn.execute(
            """
            SELECT id, branch_id, service_id, customer_id, starts_at, ends_at,
                   status, price_at_booking, created_at, updated_at
            FROM appointments
            WHERE id = %(id)s
            """,
            {"id": id},
        ).fetchone()
        return to_appointment_object(row) if row else None

    def get_for_update(self, id: UUID) -> Appointment | None:
        """Like get, but locks the row until the transaction ends.

        Used before changing the status. If two requests cancel or complete the
        same appointment at once, the second waits here, then reads the new
        status and fails the SCHEDULED check instead of overwriting it.
        """
        row = self.conn.execute(
            """
            SELECT id, branch_id, service_id, customer_id, starts_at, ends_at,
                   status, price_at_booking, created_at, updated_at
            FROM appointments
            WHERE id = %(id)s
            FOR UPDATE
            """,
            {"id": id},
        ).fetchone()
        return to_appointment_object(row) if row else None

    def save(self, appointment: Appointment) -> None:
        self.conn.execute(
            """
            UPDATE appointments
            SET status = %(status)s, updated_at = %(updated_at)s
            WHERE id = %(id)s
            """,
            {
                "id": appointment.id,
                "status": appointment.status.value,
                "updated_at": appointment.updated_at,
            },
        )

    def list_overlapping(self, branch_id: UUID, slot: TimeSlot) -> list[Appointment]:
        """Scheduled appointments at the branch whose time overlaps the slot.

        Ranges are half-open, like TimeSlot, so a booking ending at 10:30 does
        not clash with one starting at 10:30. The status is written into the
        SQL so Postgres can use the index behind no_overlapping_appointments.
        """
        rows = self.conn.execute(
            """
            SELECT id, branch_id, service_id, customer_id, starts_at, ends_at,
                   status, price_at_booking, created_at, updated_at
            FROM appointments
            WHERE branch_id = %(branch_id)s
              AND status = 'SCHEDULED'
              AND tstzrange(starts_at, ends_at) && tstzrange(%(starts_at)s, %(ends_at)s)
            """,
            {"branch_id": branch_id, "starts_at": slot.starts_at, "ends_at": slot.ends_at},
        ).fetchall()
        return [to_appointment_object(row) for row in rows]

    def list_page(
        self,
        limit: int,
        offset: int,
        branch_id: UUID | None = None,
        status: AppointmentStatus | None = None,
        on_date: date | None = None,
    ) -> list[Appointment]:
        """One page of appointments. Filters are optional and combine with AND.

        on_date is the local calendar day at each appointment's own branch, so
        2026-10-20 at a Riyadh branch means 00:00-24:00 Riyadh time.
        """
        params = filter_params(branch_id, status, on_date)
        params["limit"] = limit
        params["offset"] = offset
        rows = self.conn.execute(
            """
            SELECT a.id, a.branch_id, a.service_id, a.customer_id, a.starts_at, a.ends_at,
                   a.status, a.price_at_booking, a.created_at, a.updated_at
            FROM appointments a
            JOIN branches b ON b.id = a.branch_id
            WHERE """
            + APPOINTMENT_FILTERS
            + """
            ORDER BY a.starts_at, a.id
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params,
        ).fetchall()
        return [to_appointment_object(row) for row in rows]

    def count(
        self,
        branch_id: UUID | None = None,
        status: AppointmentStatus | None = None,
        on_date: date | None = None,
    ) -> int:
        """How many appointments match the same filters as list_page."""
        row = self.conn.execute(
            """
            SELECT count(*) AS total
            FROM appointments a
            JOIN branches b ON b.id = a.branch_id
            WHERE """ + APPOINTMENT_FILTERS,
            filter_params(branch_id, status, on_date),
        ).fetchone()
        return row["total"]


# Shared by AppointmentRepository.list_page and count, so both always agree.
# A filter switches itself off when its value is None, so the SQL text is
# fixed and never built from user input.
APPOINTMENT_FILTERS = """
    (%(branch_id)s::uuid IS NULL OR a.branch_id = %(branch_id)s)
    AND (%(status)s::text IS NULL OR a.status = %(status)s)
    AND (%(on_date)s::date IS NULL
         OR (a.starts_at AT TIME ZONE b.timezone)::date = %(on_date)s)
"""


def filter_params(
    branch_id: UUID | None, status: AppointmentStatus | None, on_date: date | None
) -> dict:
    """The named values APPOINTMENT_FILTERS expects."""
    return {
        "branch_id": branch_id,
        "status": status.value if status else None,
        "on_date": on_date,
    }


def to_appointment_object(row: dict) -> Appointment:
    """Build an Appointment from a database row."""
    return Appointment(
        id=row["id"],
        branch_id=row["branch_id"],
        service_id=row["service_id"],
        customer_id=row["customer_id"],
        slot=TimeSlot(row["starts_at"], row["ends_at"]),
        status=AppointmentStatus(row["status"]),
        price_at_booking=row["price_at_booking"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
