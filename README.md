# Car Wash Operations API

**Faiqa Nasir** · Junior Backend Developer assessment, Apex AI Arabia ·
submitted 2026-10-17 03:21 PKT (UTC+05:00)

An API for a car wash company with several branches. It stores customers,
branches, services and appointments.

Built with: Python, FastAPI, PostgreSQL, Docker.

**Demo token:** `demo-token-change-me` (every endpoint needs it)

Other documents:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): how the code is organised and why
- [docs/AI_USAGE.md](docs/AI_USAGE.md): how AI was used
- [API description](#api-description): every endpoint, in the browser

## Start the app

You only need [Docker](https://docs.docker.com/get-docker/) installed.

```bash
docker compose up --build
```

This one command:

1. starts the database
2. creates the tables
3. adds sample data (branches, services, customers)
4. starts the API

Open **http://localhost:8000/docs** in your browser. You can try every
endpoint there.

Every endpoint needs a password (a "token"). Click **Authorize** and enter:

```
demo-token-change-me
```

To run the tests:

```bash
docker compose exec api pytest
```

## Environment variables

Docker sets these for you (see `docker-compose.yml`):

```env
DATABASE_URL=postgresql://carwash:carwash@db:5432/carwash
API_TOKEN=demo-token-change-me
TEST_DATABASE_URL=postgresql://carwash:carwash@db:5432/carwash_test
```

No real passwords are saved in this repository.

## Sample data

The sample data always uses the same ids, so you can copy them into requests:

| Type | id | Name and details |
|---|---|---|
| Branch | `00000000-0000-0000-0000-00000000b001` | Riyadh - Olaya (Riyadh time, +03:00) |
| Branch | `00000000-0000-0000-0000-00000000b002` | Dubai - Marina (Dubai time, +04:00) |
| Service | `00000000-0000-0000-0000-00000000a002` | Exterior Wash, 30 minutes, 45.00 |
| Customer | `00000000-0000-0000-0000-00000000c001` | Sara Al-Harbi |

In total there are 2 branches, 4 services and 5 customers. All are made up.

## Tests

There are 28 tests.

If no database is running, the API tests are skipped.

## API description

While the app runs, you can see and try every endpoint at
http://localhost:8000/docs.

## Examples

```bash
TOKEN=demo-token-change-me
API=http://localhost:8000
```

Every request sends the token in the `Authorization` header.

**See all branches**

```bash
curl "$API/branches" -H "Authorization: Bearer $TOKEN"
```
```json
{"total": 2, "limit": 20, "offset": 0,
 "items": [{"id": "00000000-0000-0000-0000-00000000b002", "name": "Dubai - Marina", "timezone": "Asia/Dubai"}, ...]}
```

Every list is split into pages. `limit` is how many items you get (1 to
100), `offset` is how many to skip, and `total` is how many exist.

**Add a customer**

```bash
curl -X POST "$API/customers" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Noor Ali", "email": "noor@example.com", "phone": "+966500000009"}'
```

**Book an appointment**

The time must include a timezone, like `+03:00`.

```bash
curl -X POST "$API/appointments" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"branch_id": "00000000-0000-0000-0000-00000000b001",
       "customer_id": "00000000-0000-0000-0000-00000000c001",
       "service_id": "00000000-0000-0000-0000-00000000a002",
       "starts_at": "2030-01-10T10:00:00+03:00"}'
```
```json
{"id": "…", "branch_id": "…b001", "service_id": "…a002", "customer_id": "…c001",
 "starts_at": "2030-01-10T07:00:00Z", "ends_at": "2030-01-10T07:30:00Z",
 "status": "SCHEDULED", "price_at_booking": "45.00", "created_at": "…", "updated_at": "…"}
```

Times always come back in UTC (the `Z` at the end). 10:00 in Riyadh is 07:00
UTC.

If someone now tries to book 10:15 at the same branch, they get an error:

```json
{"error": {"code": "overlapping_booking",
           "message": "this slot at the branch is already booked from 2030-01-10T07:00:00Z to 2030-01-10T07:30:00Z",
           "details": []}}
```

**See a branch's appointments for one day**

```bash
curl "$API/branches/00000000-0000-0000-0000-00000000b001/appointments?date=2030-01-10&status=SCHEDULED" \
  -H "Authorization: Bearer $TOKEN"
```

The date means that day in the branch's own time. `/appointments` works the
same way for all branches, and can also filter by `branch_id`.

**Cancel or complete an appointment**

```bash
curl -X POST "$API/appointments/<id>/cancel" -H "Authorization: Bearer $TOKEN"
curl -X POST "$API/appointments/<id>/complete" -H "Authorization: Bearer $TOKEN"
```

Only a SCHEDULED appointment can be cancelled or completed. Trying again gives
an error: `"appointment is already cancelled"`.

### All endpoints

All endpoints need the token:

| Method | Path |
|---|---|
| GET | `/branches` |
| GET | `/services` |
| POST | `/customers` |
| GET | `/customers` |
| GET | `/customers/{customer_id}` |
| POST | `/appointments` |
| GET | `/appointments` |
| GET | `/appointments/{appointment_id}` |
| GET | `/branches/{branch_id}/appointments` |
| POST | `/appointments/{appointment_id}/cancel` |
| POST | `/appointments/{appointment_id}/complete` |
