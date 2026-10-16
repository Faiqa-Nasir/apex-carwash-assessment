# Architecture note

## 1. Tech stack

| Part | Choice |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI |
| Database | PostgreSQL 16 |
| Database access | plain SQL (psycopg 3) |
| Tables | pgmigrate |
| Tests | pytest |
| Setup | Docker Compose |

## 2. Architecture

```
request -> endpoints -> services -> repositories -> database
                           |
             domain model (business rules)
```

| Layer | Folder | Job |
|---|---|---|
| Endpoints | `app/api/` | receive the request |
| Services | `app/booking/services/` | one function per action, e.g. "book" |
| Domain model (business rules) | `app/booking/domain/` | the rules, e.g. "no booking in the past" |
| Repositories | `app/booking/repositories.py` | all the SQL |

- **Endpoints are short:** check the token, call one service function,
  return the result.
- **Business rules are plain Python**, with no database or HTTP code.
- **Each request is one transaction:** everything is saved at the end, or
  nothing if something fails.

**Why:** I'm following the structure from *Architecture Patterns with
Python* ("Cosmic Python"), kept small.

## 3. Why domain-driven design and plain SQL

**Light domain-driven design:** the rules live in plain classes
(`Appointment`, `TimeSlot`), in one place, and are tested in milliseconds
without a database.

**Plain SQL instead of an ORM:** with four tables, plain SQL is shorter and
easy to read.

**If the system grows** to many more tables, that hand-written code gets
repetitive, and I would switch to an ORM like SQLAlchemy. Only
`repositories.py` would need to change.

To make that switch easier, I would first add an abstract repository
interface, as Cosmic Python does. The services would depend on the interface,
not on the SQL code, so a SQLAlchemy version could replace the plain SQL
version without changing the services. It would also allow fake repositories
for fast tests. I left it out for now, because with one database version it
would only add extra code.

## 4. Assumptions

- Customers aren't linked to branches.
- Services aren't branch-specific.
- Customers can book at any branch, even two branches at the same time.
- No opening hours and no break between washes.
- This is a very small system, built to test my coding. If it were large, I
  might choose differently, for example an ORM to reduce boilerplate code.

## 5. Data model

| Table | Columns | Database rules |
|---|---|---|
| `branches` | id, name, timezone | name not empty |
| `services` | id, name, duration_minutes, price | duration > 0, price >= 0 |
| `customers` | id, name, email, phone, created_at | unique email (lowercase) |
| `appointments` | id, branch_id, service_id, customer_id, starts_at, ends_at, status, price_at_booking, created_at, updated_at | ids must exist; end after start; valid status; no overlapping SCHEDULED appointments per branch |

Times are saved in UTC. Each branch's timezone is used for the `date` filter.

## 6. APIs

Every endpoint needs the token.

- Branches and services: `GET /branches`, `GET /services`.
- Customers: `POST /customers`, `GET /customers`, `GET /customers/{id}`.
- Appointments: `POST /appointments`, `GET /appointments`,
  `GET /appointments/{id}`, `GET /branches/{id}/appointments`,
  `POST /appointments/{id}/cancel`, `POST /appointments/{id}/complete`.

Lists return pages (`limit`, `offset`, `total`). Full details are in the
README and in Swagger at `/docs`.

## 7. Concurrency and errors

### Concurrency

- **One transaction per request:** the Unit of Work opens a transaction, and
  saves everything at the end, or nothing if any step fails. So a booking
  is never half saved.
- **Double bookings:** the code checks for an overlapping booking at the
  branch and returns 409 if there is one.
- **Two bookings at the same moment:** the database refuses the second one,
  and the Unit of Work rolls it back.
- **Back-to-back is fine:** a booking can start exactly when another ends.
- **Cancel and complete:** the appointment is locked while it changes, so if
  two requests come together, only the first one works.
- **Tested:** both cases were tested by sending 10 requests at once, and only
  one succeeds.

### Errors

The errors the code raises:

| Error | Status | When |
|---|---|---|
| `NotFound` | 404 | the branch, customer, service or appointment doesn't exist |
| `PastBookingTime` | 400 | the start time is in the past |
| `ValidationError` | 400 | a business rule is broken, e.g. an empty name or a time without a timezone |
| `OverlappingBooking` | 409 | the slot at the branch is already booked |
| `DuplicateEmail` | 409 | a customer already uses that email |
| `InvalidStatusTransition` | 409 | the appointment is already cancelled or completed |
| `Unauthorized` | 401 | the token is missing or wrong |

Badly formed requests get 422, and anything unexpected gets 500.

## 8. Security

- All input is checked before the code runs (ids, timezones, email, lengths,
  page size).
- No SQL injection: values are always passed separately from the SQL.
- A token protects every endpoint, reads included.
- No real secrets in git; only the demo token.
- Error messages never show internals or repeat what the user sent.

## 9. Trade-offs

- **Plain SQL vs ORM:** the options were plain SQL, SQLAlchemy Core (SQL
  written in Python) or the SQLAlchemy ORM (tables as Python classes). I
  chose plain SQL mainly because this is a small project: four tables, so an
  ORM would add more setup than it saves. The cost is turning database rows
  into Python objects by hand, which grows with every new table.
- **pgmigrate vs Alembic:** for a small project with a plain SQL schema,
  pgmigrate is the simplest tool that does the job. If the team already used
  Alembic, or we moved to SQLAlchemy, I'd switch to Alembic.

## 10. Next improvements

- User accounts with roles, and rate limiting.
- Opening hours and breaks between washes.
- Per-branch services and prices.
- Faster paging for large tables.
- Request ids in logs and error responses.
- Switch to SQLAlchemy if the tables grow a lot.
