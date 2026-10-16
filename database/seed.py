"""Idempotent seed: 2 branches, 4 services, 5 customers (fictional data only).

Run with: python -m database.seed

Every row has a fixed id, so running it again inserts nothing new
(ON CONFLICT DO NOTHING). The fixed ids also make the API easy to try by hand.
"""

import psycopg

from app.config import get_settings

BRANCHES = [
    ("00000000-0000-0000-0000-00000000b001", "Riyadh - Olaya", "Asia/Riyadh"),
    ("00000000-0000-0000-0000-00000000b002", "Dubai - Marina", "Asia/Dubai"),
]

SERVICES = [
    ("00000000-0000-0000-0000-00000000a001", "Express Wash", 15, "25.00"),
    ("00000000-0000-0000-0000-00000000a002", "Exterior Wash", 30, "45.00"),
    ("00000000-0000-0000-0000-00000000a003", "Interior Clean", 45, "60.00"),
    ("00000000-0000-0000-0000-00000000a004", "Full Detail", 90, "180.00"),
]

CUSTOMERS = [
    ("00000000-0000-0000-0000-00000000c001", "Sara Al-Harbi", "sara@example.com", "+966500000001"),
    ("00000000-0000-0000-0000-00000000c002", "Omar Khalid", "omar@example.com", "+966500000002"),
    ("00000000-0000-0000-0000-00000000c003", "Lina Haddad", "lina@example.com", None),
    ("00000000-0000-0000-0000-00000000c004", "Yusuf Rahman", "yusuf@example.com", "+971500000004"),
    ("00000000-0000-0000-0000-00000000c005", "Mariam Saeed", "mariam@example.com", None),
]


def seed(database_url: str) -> None:
    # The connection block commits at the end, or rolls back if anything fails.
    with psycopg.connect(database_url) as conn:
        conn.cursor().executemany(
            "INSERT INTO branches (id, name, timezone) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            BRANCHES,
        )
        conn.cursor().executemany(
            "INSERT INTO services (id, name, duration_minutes, price) VALUES (%s, %s, %s, %s)"
            " ON CONFLICT DO NOTHING",
            SERVICES,
        )
        conn.cursor().executemany(
            "INSERT INTO customers (id, name, email, phone) VALUES (%s, %s, %s, %s)"
            " ON CONFLICT DO NOTHING",
            CUSTOMERS,
        )


if __name__ == "__main__":
    seed(get_settings().database_url)
    print("seeded 2 branches, 4 services, 5 customers")
