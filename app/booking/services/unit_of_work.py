"""The transaction boundary.

    with UnitOfWork(dsn) as uow:
        customer = uow.customers.get(customer_id)
        uow.appointments.add(appointment)

Everything inside the block is one database transaction: committed if the
block finishes, rolled back if anything raises. This is the only place in
the codebase that commits.
"""

import psycopg
from psycopg.rows import dict_row

from app.booking.repositories import (
    AppointmentRepository,
    BranchRepository,
    CustomerRepository,
    ServiceRepository,
)


class UnitOfWork:
    branches: BranchRepository
    services: ServiceRepository
    customers: CustomerRepository
    appointments: AppointmentRepository

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def __enter__(self) -> "UnitOfWork":
        # Rows come back as dicts, and timestamps come back in UTC.
        self.conn = psycopg.connect(self.dsn, row_factory=dict_row, options="-c timezone=UTC")
        self.branches = BranchRepository(self.conn)
        self.services = ServiceRepository(self.conn)
        self.customers = CustomerRepository(self.conn)
        self.appointments = AppointmentRepository(self.conn)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
