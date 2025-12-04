# Meeting Room Booking API

A REST API system for managing meeting room bookings with conflict detection, validation, and multi-user support.

## Table of Contents
- [Features](#features)
- [Architecture & Design Patterns](#architecture--design-patterns)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Example Usage](#example-usage)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Design Decisions & Assumptions](#design-decisions--assumptions)

---

## Features

### Features (Required)
- ✅ Create meeting room bookings with room identifier and timing
- ✅ Room names in MACRO_CASE format (e.g., EVEREST, KINABALU, RINJANI)
- ✅ Booking timing in 'YYYY-MM-DD HH:MM' format with 10-minute increments
- ✅ Automatic conflict detection (rejects overlapping bookings)
- ✅ Query bookings by room or user for a specific date
- ✅ Multi-user support with concurrent request handling

### Additional Improvements
- ✅ Comprehensive input validation (see [Validations](#validations))
- ✅ Interactive API documentation (Swagger UI at `/docs`)
- ✅ HTML frontend for easy testing
- ✅ Application logging for debugging and monitoring
- ✅ 10 automated tests covering all scenarios
- ✅ Proper HTTP status codes (201, 200, 400, 409)

---

## Architecture & Design Patterns

This application follows industry-standard design patterns:

### **1. Layered Architecture (Three-Tier)**
```
┌─────────────────────────────────────┐
│   Presentation Layer                │
│   - HTML Frontend (static/)         │
│   - FastAPI Auto-docs (/docs)       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Business Logic Layer              │
│   - API Endpoints (app.py)          │
│   - Validation Rules                │
│   - Conflict Detection              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Data Access Layer                 │
│   - Database Config (database.py)   │
│   - SQLModel ORM                    │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Data Layer                        │
│   - SQLite Database (bookings.db)   │
└─────────────────────────────────────┘
```

### **2. MVC-Inspired Pattern**
- **Model**: `models.py` - Defines `Booking` data structure
- **View**: `static/index.html` + FastAPI auto-generated documentation
- **Controller**: `app.py` - Handles HTTP requests and business logic

### **3. Dependency Injection**
- FastAPI's `Depends()` pattern for database session management
- Promotes testability and loose coupling

### **4. ORM (Object-Relational Mapping)**
- SQLModel abstracts database operations
- Python objects automatically mapped to SQL tables

### **5. RESTful API Design**
- Resource-based URLs (`/bookings`)
- Standard HTTP methods (GET, POST)
- Proper status codes (201 Created, 409 Conflict, etc.)
- JSON request/response format

### **6. Context Manager Pattern**
- Lifespan context for startup/shutdown events
- Database sessions with automatic cleanup

---

## Prerequisites

- **Python 3.10+** (tested on Python 3.12)
- **pip** (Python package manager)

---

## Setup Instructions

### 1. Clone or Download the Project
```bash
cd meeting-booking-app
```

### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlmodel` - SQL database ORM
- `pytest` - Testing framework
- `httpx` - HTTP client for tests

---

## Running the Application

### Method 1: Direct Execution (Recommended)
```bash
python app.py
```

### Method 2: Using uvicorn
```bash
uvicorn app:app --reload
```

**Server will start on:** `http://localhost:8000`

You should see:
```
INFO: Starting up Meeting Room Booking API...
INFO: Database initialized successfully
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete.
```

---

## API Endpoints

### 1. Create Booking
**Endpoint:** `POST /bookings`

**Request Body:**
```json
{
  "room": "EVEREST",
  "user": "john_doe",
  "start_time": "2025-12-10 14:30",
  "end_time": "2025-12-10 15:30"
}
```

**Success Response (201 Created):**
```json
{
  "id": 1,
  "room": "EVEREST",
  "user": "john_doe",
  "start_time": "2025-12-10T14:30:00",
  "end_time": "2025-12-10T15:30:00"
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "Room must be in MACRO_CASE"
}
```

### 2. Get Bookings
**Endpoint:** `GET /bookings`

**Query Parameters:**
- `date` (required): Date in YYYY-MM-DD format
- `room` or `user` (required): Exactly one must be provided

**Example Requests:**
```bash
# Get bookings for a room
GET /bookings?date=2025-12-10&room=EVEREST

# Get bookings for a user
GET /bookings?date=2025-12-10&user=john_doe
```

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "room": "EVEREST",
    "user": "john_doe",
    "start_time": "2025-12-10T14:30:00",
    "end_time": "2025-12-10T15:30:00"
  }
]
```

---

## Example Usage

### Using the Web Interface
1. Start the server: `python app.py`
2. Open browser: `http://localhost:8000`
3. Use the form to create and query bookings

### Using Interactive API Docs (Swagger UI)
1. Start the server: `python app.py`
2. Open browser: `http://localhost:8000/docs`
3. Click "Try it out" on any endpoint
4. Fill in parameters and click "Execute"

### Using curl

#### Create a booking:
```bash
curl -X POST "http://localhost:8000/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "room": "EVEREST",
    "user": "john_doe",
    "start_time": "2025-12-10 14:30",
    "end_time": "2025-12-10 15:30"
  }'
```

#### Get bookings for a room:
```bash
curl "http://localhost:8000/bookings?date=2025-12-10&room=EVEREST"
```

#### Get bookings for a user:
```bash
curl "http://localhost:8000/bookings?date=2025-12-10&user=john_doe"
```

#### Test validation (this will fail):
```bash
# Lowercase room name - will return 400 error
curl -X POST "http://localhost:8000/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "room": "everest",
    "user": "john_doe",
    "start_time": "2025-12-10 14:30",
    "end_time": "2025-12-10 15:30"
  }'
```

---

## Testing

### Run All Tests
```bash
pytest test_app.py -v
```

### Run Specific Test
```bash
pytest test_app.py::test_create_booking_success -v
```

### Test Coverage
The test suite includes 10 comprehensive tests:
1. ✅ Successfully create booking
2. ✅ Reject lowercase room name
3. ✅ Reject invalid minute increments
4. ✅ Reject bookings in the past
5. ✅ Reject bookings too far in future
6. ✅ Reject invalid room name characters
7. ✅ Reject overlapping bookings
8. ✅ Get bookings by room
9. ✅ Get bookings by user
10. ✅ Reject queries with both filters

**Expected Output:**
```
========== 10 passed in 0.33s ==========
```

---

## Project Structure

```
meeting-booking-app/
├── app.py              # Main application with API endpoints
├── models.py           # Database models (Booking)
├── database.py         # Database configuration and session management
├── test_app.py         # Automated tests
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── bookings.db        # SQLite database (created automatically)
├── static/
│   └── index.html     # Web frontend
└── __pycache__/       # Python cache (auto-generated)
```

---

## Design Decisions & Assumptions

### Core Assumptions

1. **Booking Duration**
   - Users specify both start_time and end_time
   - No restrictions on booking duration (can be 30 minutes, 2 hours, etc.)
   - *Rationale:* Flexible duration makes the system more realistic and useful 

2. **Room Management**
   - No predefined list of rooms
   - Any MACRO_CASE string is accepted as a valid room identifier
   - *Rationale:* Requirements don't specify room validation beyond format

3. **User Authentication**
   - No authentication system implemented
   - User name is just a string identifier
   - Two people can have the same name (treated as separate users)
   - *Rationale:* Not required in specification, focus on booking logic

4. **Time Zone**
   - All times are in **server local time**
   - No timezone support

5. **Concurrent Users**
   - FastAPI handles concurrent requests natively
   - Database uses SQLite with proper locking
   - *Rationale:* Meets multi-user requirement

### Additional Validations

Beyond the basic requirements, the following validations were added:

#### 1. **Room Name Validations**
- Must be in UPPERCASE (MACRO_CASE)
- Only letters (A-Z) and underscores (_) allowed
- Maximum 50 characters
- Cannot be empty or whitespace only

**Examples:**
- Valid: `EVEREST`, `MOUNT_KINABALU`, `MEETING_ROOM_A`
- Invalid: `everest`, `EVEREST123`, `EVER@ST`, `EVEREST-ROOM`

#### 2. **Time Validations**
- **No Past Bookings**: Cannot book meetings in the past
- **Future Limit**: Cannot book more than 1 year in advance
- **10-Minute Increments**: Both start and end time minutes must be 00, 10, 20, 30, 40, or 50
- **End After Start**: End time must be after start time
- **Required Fields**: Both start_time and end_time are required

**Rationale:** Prevents unrealistic bookings and maintains data quality

#### 3. **User Booking Limit**
- Maximum **5 bookings per day per user**
- Prevents abuse and resource hogging
- *Rationale:* Business logic to ensure fair resource allocation

#### 4. **Conflict Detection**
- Checks if room is already booked during requested time
- Uses interval overlap logic: checks if new booking overlaps with any existing booking
- Returns HTTP 409 (Conflict) status code

#### 5. **Query Validations**
- Must provide exactly one filter (room OR user, not both)
- Date must be in valid YYYY-MM-DD format
- Room name must be in MACRO_CASE when querying by room

### HTTP Status Codes

Following REST best practices:
- **200 OK**: Successful GET requests
- **201 Created**: Successfully created booking
- **400 Bad Request**: Invalid input (validation failed)
- **409 Conflict**: Booking conflict (room already booked)

### Error Handling

All errors return JSON with descriptive messages:
```json
{
  "detail": "Descriptive error message"
}
```

### Logging

Application logs all important events:
- Server startup/shutdown
- Booking requests received
- Validation failures
- Successful bookings
- Conflicts detected
- Query operations

**Log Format:**
```
2025-12-04 22:30:15 - __main__ - INFO - Booking created successfully - ID: 1
```

---

## Technology Stack

- **FastAPI**: Modern, fast web framework with automatic API documentation
- **SQLModel**: SQL database ORM combining SQLAlchemy and Pydantic
- **SQLite**: Lightweight, serverless database (perfect for development)
- **Uvicorn**: Fast ASGI server
- **Pytest**: Industry-standard testing framework
- **Python 3.10+**: Latest Python features (type hints, union types)

---

## Future Enhancements (Not Implemented)

If given more time, these features could be added:
- DELETE endpoint to cancel bookings
- PATCH endpoint to modify bookings
- Authentication and authorization
- Pagination for large result sets
- Filter by date range (not just single date)
- Recurring bookings (weekly meetings)
- Email notifications
- Room availability checker endpoint
- PostgreSQL/MySQL for production
- Docker containerization
- Environment configuration (.env file)

---
