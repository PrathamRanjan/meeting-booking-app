import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app import app
from database import get_session
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
import logging

# Disable logging during tests for cleaner output
logging.disable(logging.CRITICAL)

# Create a test database in memory (doesn't save to disk)
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# Override the get_session to use test database
@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# Test 1: Successfully create a booking
def test_create_booking_success(client):
    # Create a booking for tomorrow at 10:00 to 11:00
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

    response = client.post(
        "/bookings",
        json={
            "room": "EVEREST",
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    assert response.status_code == 201  # Changed from 200 to 201 (Created)
    data = response.json()
    assert data["room"] == "EVEREST"
    assert data["user"] == "john_doe"


# Test 2: Reject booking with lowercase room name
def test_create_booking_lowercase_room(client):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

    response = client.post(
        "/bookings",
        json={
            "room": "everest",  # lowercase - should fail
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    assert response.status_code == 400
    assert "MACRO_CASE" in response.json()["detail"]


# Test 3: Reject booking with invalid minutes (not 10 minute increment)
def test_create_booking_invalid_minutes(client):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=5, second=0, microsecond=0)  # :05 is invalid
    end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

    response = client.post(
        "/bookings",
        json={
            "room": "EVEREST",
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    assert response.status_code == 400
    assert "10 minute increments" in response.json()["detail"]


# Test 4: Reject booking in the past
def test_create_booking_in_past(client):
    yesterday = datetime.now() - timedelta(days=1)
    start_time = yesterday.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = yesterday.replace(hour=11, minute=0, second=0, microsecond=0)

    response = client.post(
        "/bookings",
        json={
            "room": "EVEREST",
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    assert response.status_code == 400
    assert "past" in response.json()["detail"]


# Test 5: Reject booking too far in future (more than 1 year)
def test_create_booking_too_far_future(client):
    far_future = datetime.now() + timedelta(days=400)  # More than 1 year
    start_time = far_future.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = far_future.replace(hour=11, minute=0, second=0, microsecond=0)

    response = client.post(
        "/bookings",
        json={
            "room": "EVEREST",
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    assert response.status_code == 400
    assert "1 year" in response.json()["detail"]


# Test 6: Reject booking with invalid room name (contains numbers)
def test_create_booking_invalid_room_name(client):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

    response = client.post(
        "/bookings",
        json={
            "room": "EVEREST123",  # Contains numbers - should fail
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    assert response.status_code == 400
    assert "uppercase letters and underscores" in response.json()["detail"]


# Test 7: Reject overlapping bookings
def test_create_booking_overlap(client):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

    # Create first booking
    client.post(
        "/bookings",
        json={
            "room": "EVEREST",
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    # Try to book the same room at the same time - should fail
    response = client.post(
        "/bookings",
        json={
            "room": "EVEREST",
            "user": "jane_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    assert response.status_code == 409
    assert "conflict" in response.json()["detail"]


# Test 8: Get bookings by room
def test_get_bookings_by_room(client):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

    # Create a booking
    client.post(
        "/bookings",
        json={
            "room": "KINABALU",
            "user": "john_doe",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    # Query bookings for that room and date
    response = client.get(
        f"/bookings?date={start_time.strftime('%Y-%m-%d')}&room=KINABALU"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["room"] == "KINABALU"


# Test 9: Get bookings by user
def test_get_bookings_by_user(client):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)

    # Create a booking
    client.post(
        "/bookings",
        json={
            "room": "RINJANI",
            "user": "alice",
            "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M")
        }
    )

    # Query bookings for that user and date
    response = client.get(
        f"/bookings?date={start_time.strftime('%Y-%m-%d')}&user=alice"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user"] == "alice"


# Test 10: Reject query with both room and user
def test_get_bookings_both_filters(client):
    tomorrow = datetime.now() + timedelta(days=1)

    response = client.get(
        f"/bookings?date={tomorrow.strftime('%Y-%m-%d')}&room=EVEREST&user=john"
    )

    assert response.status_code == 400
    assert "exactly one filter" in response.json()["detail"]
