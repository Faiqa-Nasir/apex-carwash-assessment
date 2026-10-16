-- Create branches, services, customers and appointments.
--
-- The rules that must hold even when two requests run at the same time live
-- here, as constraints, not only in Python:
-- - a customer email is unique (uq_customers_email -> DuplicateEmail, 409)
-- - two SCHEDULED appointments at one branch never overlap
--   (no_overlapping_appointments -> OverlappingBooking, 409)

-- btree_gist lets one exclusion constraint compare a uuid (=) and a time range (&&).
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE branches (
    id       uuid PRIMARY KEY,
    name     text NOT NULL CHECK (name <> ''),
    timezone text NOT NULL
);

CREATE TABLE services (
    id               uuid PRIMARY KEY,
    name             text NOT NULL CHECK (name <> ''),
    duration_minutes integer NOT NULL CHECK (duration_minutes > 0),
    price            numeric(10, 2) NOT NULL CHECK (price >= 0)
);

CREATE TABLE customers (
    id         uuid PRIMARY KEY,
    name       text NOT NULL CHECK (name <> ''),
    email      text NOT NULL,
    phone      text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_customers_email UNIQUE (email)
);

CREATE TABLE appointments (
    id               uuid PRIMARY KEY,
    branch_id        uuid NOT NULL REFERENCES branches (id),
    service_id       uuid NOT NULL REFERENCES services (id),
    customer_id      uuid NOT NULL REFERENCES customers (id),
    starts_at        timestamptz NOT NULL,
    ends_at          timestamptz NOT NULL,
    status           text NOT NULL
        CHECK (status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED')),
    price_at_booking numeric(10, 2) NOT NULL CHECK (price_at_booking >= 0),
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at),
    -- One appointment at a time per branch: if two requests pass the Python overlap check at
    -- the same moment, the second INSERT fails here. The index behind this
    -- constraint also serves the overlap lookup when booking.
    CONSTRAINT no_overlapping_appointments EXCLUDE USING gist (
        branch_id WITH =,
        tstzrange(starts_at, ends_at) WITH &&
    ) WHERE (status = 'SCHEDULED')
);

-- For lookups by customer, and for the appointment list ordered by start time.
CREATE INDEX ix_appointments_customer_id ON appointments (customer_id);
CREATE INDEX ix_appointments_starts_at ON appointments (starts_at);
