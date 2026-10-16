"""API tests: real HTTP requests against a real, freshly seeded Postgres.

Seed ids used below (see database/seed.py):
  RIYADH branch (Asia/Riyadh, +03:00), DUBAI branch (Asia/Dubai, +04:00),
  EXTERIOR_WASH service (30 min, 45.00), SARA and OMAR customers.
"""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

RIYADH = "00000000-0000-0000-0000-00000000b001"
DUBAI = "00000000-0000-0000-0000-00000000b002"
EXTERIOR_WASH = "00000000-0000-0000-0000-00000000a002"
SARA = "00000000-0000-0000-0000-00000000c001"
OMAR = "00000000-0000-0000-0000-00000000c002"

TEN_AM = "2030-01-10T10:00:00+03:00"  # 07:00 UTC


def booking(starts_at=TEN_AM, branch_id=RIYADH, customer_id=SARA, service_id=EXTERIOR_WASH):
    return {
        "branch_id": branch_id,
        "customer_id": customer_id,
        "service_id": service_id,
        "starts_at": starts_at,
    }


# --- happy paths -------------------------------------------------------------


def test_book_appointment(client, auth):
    response = client.post("/appointments", json=booking(), headers=auth)

    assert response.status_code == 201
    appointment = response.json()
    assert appointment["status"] == "SCHEDULED"
    assert appointment["starts_at"] == "2030-01-10T07:00:00Z"  # stored and returned in UTC
    assert appointment["ends_at"] == "2030-01-10T07:30:00Z"  # 30-minute service
    assert appointment["price_at_booking"] == "45.00"

    fetched = client.get(f"/appointments/{appointment['id']}", headers=auth)
    assert fetched.json() == appointment


def test_bookings_that_do_not_clash_are_allowed(client, auth):
    client.post("/appointments", json=booking(), headers=auth)  # 10:00-10:30 Riyadh

    starts_when_first_ends = booking("2030-01-10T10:30:00+03:00", customer_id=OMAR)
    assert (
        client.post("/appointments", json=starts_when_first_ends, headers=auth).status_code == 201
    )

    same_time_other_branch = booking(branch_id=DUBAI, customer_id=OMAR)
    assert (
        client.post("/appointments", json=same_time_other_branch, headers=auth).status_code == 201
    )


def test_cancel_frees_the_slot(client, auth):
    first = client.post("/appointments", json=booking(), headers=auth).json()

    cancelled = client.post(f"/appointments/{first['id']}/cancel", headers=auth)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    rebooked = client.post("/appointments", json=booking(customer_id=OMAR), headers=auth)
    assert rebooked.status_code == 201


def test_lists_are_paginated_with_a_total(client, auth):
    page = client.get("/services", params={"limit": 2, "offset": 1}, headers=auth).json()

    assert page["total"] == 4
    assert page["limit"] == 2
    assert page["offset"] == 1
    assert len(page["items"]) == 2


def test_date_filter_uses_the_branch_local_day(client, auth):
    # 01:00 on the 11th in Riyadh is still the 10th in UTC (22:00).
    client.post("/appointments", json=booking("2030-01-11T01:00:00+03:00"), headers=auth)

    on_11th = client.get(
        f"/branches/{RIYADH}/appointments", params={"date": "2030-01-11"}, headers=auth
    )
    on_10th = client.get(
        f"/branches/{RIYADH}/appointments", params={"date": "2030-01-10"}, headers=auth
    )
    assert on_11th.json()["total"] == 1
    assert on_10th.json()["total"] == 0


# --- unhappy paths -----------------------------------------------------------


def test_overlapping_booking_is_rejected(client, auth):
    client.post("/appointments", json=booking(), headers=auth)  # 07:00-07:30 UTC

    response = client.post(
        "/appointments", json=booking("2030-01-10T10:15:00+03:00", customer_id=OMAR), headers=auth
    )

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "overlapping_booking",
        "message": "this slot at the branch is already booked from 2030-01-10T07:00:00Z to 2030-01-10T07:30:00Z",
        "details": [],
    }


def test_concurrent_bookings_for_one_slot_only_one_wins(client, auth):
    def book(_):
        return client.post("/appointments", json=booking(), headers=auth).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        status_codes = sorted(pool.map(book, range(10)))

    assert status_codes == [201] + [409] * 9


def test_concurrent_cancel_and_complete_only_one_wins(client, auth):
    appointment = client.post("/appointments", json=booking(), headers=auth).json()
    urls = [f"/appointments/{appointment['id']}/{action}" for action in ("cancel", "complete")] * 5

    def change_status(url):
        return client.post(url, headers=auth).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        status_codes = sorted(pool.map(change_status, urls))

    assert status_codes == [200] + [409] * 9


def test_finished_appointment_cannot_change(client, auth):
    appointment = client.post("/appointments", json=booking(), headers=auth).json()
    client.post(f"/appointments/{appointment['id']}/complete", headers=auth)

    response = client.post(f"/appointments/{appointment['id']}/cancel", headers=auth)

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "appointment is already completed"


def test_booking_in_the_past_is_rejected(client, auth):
    response = client.post("/appointments", json=booking("2020-01-10T10:00:00+03:00"), headers=auth)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "past_booking_time"


def test_invalid_input_returns_422_without_echoing_values(client, auth):
    no_timezone = booking("2030-01-10T10:00:00")
    response = client.post("/appointments", json=no_timezone, headers=auth)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.starts_at"

    bad_email = {"name": "Test", "email": "secret-not-an-email"}
    response = client.post("/customers", json=bad_email, headers=auth)
    assert response.status_code == 422
    assert "secret-not-an-email" not in response.text


def test_every_endpoint_needs_a_valid_token(client):
    no_token = client.post("/appointments", json=booking())
    wrong_token = client.post(
        "/appointments", json=booking(), headers={"Authorization": "Bearer wrong"}
    )
    read_without_token = client.get("/branches")

    for response in (no_token, wrong_token, read_without_token):
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


def test_unknown_ids_return_404(client, auth):
    unknown_customer = client.post(
        "/appointments", json=booking(customer_id=str(uuid4())), headers=auth
    )
    assert unknown_customer.status_code == 404
    assert unknown_customer.json()["error"]["message"] == "customer not found"

    unknown_appointment = client.post(f"/appointments/{uuid4()}/cancel", headers=auth)
    assert unknown_appointment.status_code == 404


def test_duplicate_email_is_rejected_ignoring_case(client, auth):
    response = client.post(
        "/customers", json={"name": "Another Sara", "email": "SARA@example.com"}, headers=auth
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"
