from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles  # for serving HTML files
from fastapi.responses import FileResponse  # for serving index.html
from fastapi.middleware.cors import CORSMiddleware  # for allowing frontend to call API
from sqlmodel import Session, select
from pydantic import BaseModel  # needed for request body validation
from models import Booking
from database import create_db_and_tables, get_session
from datetime import datetime, timedelta
from contextlib import asynccontextmanager  # for modern FastAPI lifespan events
import re  # for regex validation of room names
import os  # for checking if static folder exists
import logging  # for logging application events

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# this handles startup and shutdown events (modern FastAPI way)
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Code that runs when the server starts
    logger.info("Starting up Meeting Room Booking API...")
    create_db_and_tables()
    logger.info("Database initialized successfully")
    yield  # Server runs here and handles requests
    # Code that runs when server shuts down would go here (if needed)
    logger.info("Shutting down Meeting Room Booking API...")

# this creates the API Application with lifespan event handler and documentation
app = FastAPI(
    title="Meeting Room Booking API",
    description="A REST API for booking meeting rooms with conflict detection and validation",
    version="1.0.0",
    lifespan=lifespan
)

# Allow frontend to call API (CORS - Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML, CSS, JS) if the static folder exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# this defines what data the API accepts when creating a booking
class BookingCreate(BaseModel):
    room: str
    user: str
    start_time: str
    end_time: str

# Root endpoint - serves the HTML frontend
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post(
    "/bookings",
    response_model=Booking,
    status_code=201,
    summary="Create a new meeting room booking",
    responses={
        201: {"description": "Booking created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "Booking conflict - room already booked"}
    }
)
def create_booking(
    booking_data: BookingCreate,  # accept request body instead of query params
    session: Session = Depends(get_session)
):
    """
    Create a new meeting room booking with the following validations:

    - **room**: Must be in MACRO_CASE (e.g., EVEREST, KINABALU, RINJANI)
    - **user**: User's name (cannot be empty)
    - **start_time**: Format YYYY-MM-DD HH:MM, minutes must be in 10-minute increments (00, 10, 20, 30, 40, 50)
    - **end_time**: Format YYYY-MM-DD HH:MM, minutes must be in 10-minute increments (00, 10, 20, 30, 40, 50)

    **Validations:**
    - Room name must contain only uppercase letters and underscores (max 50 characters)
    - Start time cannot be in the past
    - Start time cannot be more than 1 year in the future
    - End time must be after start time
    - Both start and end times must have minutes in 10-minute increments
    - Room must not have conflicting bookings
    - User cannot have more than 5 bookings per day

    **Example Request:**
    ```json
    {
        "room": "EVEREST",
        "user": "john_doe",
        "start_time": "2025-12-10 14:30",
        "end_time": "2025-12-10 15:30"
    }
    ```
    """
    logger.info(f"Received booking request - Room: {booking_data.room}, User: {booking_data.user}, Start: {booking_data.start_time}, End: {booking_data.end_time}")

    # 1. Check that room and user are not empty
    if not booking_data.room or not booking_data.room.strip():
        logger.warning("Booking rejected: Room name is empty")
        raise HTTPException(status_code=400, detail="Room cannot be empty")

    if not booking_data.user or not booking_data.user.strip():
        raise HTTPException(status_code=400, detail="User cannot be empty")

    # 2. Validate room is in MACRO_CASE

    if not booking_data.room.isupper():
        raise HTTPException(status_code=400, detail="Room must be in MACRO_CASE")

    # 3. Validate room name constraints (only letters and underscores, max 50 chars)
    if len(booking_data.room) > 50:
        raise HTTPException(status_code=400, detail="Room name must be 50 characters or less")

    if not re.match(r'^[A-Z_]+$', booking_data.room):
        raise HTTPException(status_code=400, detail="Room name must contain only uppercase letters and underscores")

    # 4. Parse start time

    # Accept both " " and "T" between date/time
    try:
        cleaned = booking_data.start_time.replace("T", " ").replace("%20", " ")
        start_dt = datetime.strptime(cleaned, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time format, use YYYY-MM-DD HH:MM")

    # 5. Parse end time

    try:
        cleaned_end = booking_data.end_time.replace("T", " ").replace("%20", " ")
        end_dt = datetime.strptime(cleaned_end, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid end_time format, use YYYY-MM-DD HH:MM")

    # 6. Validate minute increments for both start and end times

    if start_dt.minute % 10 != 0:
        raise HTTPException(status_code=400, detail="Start time minutes must be in 10 minute increments")

    if end_dt.minute % 10 != 0:
        raise HTTPException(status_code=400, detail="End time minutes must be in 10 minute increments")

    # 7. Validate end time is after start time

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    # 8. Check booking is not in the past
    current_time = datetime.now()
    if start_dt < current_time:
        raise HTTPException(status_code=400, detail="Cannot book meetings in the past")

    # 9. Check booking is not too far in the future (max 1 year ahead)
    max_future_date = current_time + timedelta(days=365)
    if start_dt > max_future_date:
        raise HTTPException(status_code=400, detail="Cannot book more than 1 year in advance")

    # 10. Check for overlap with existing bookings
    statement = select(Booking).where(
        Booking.room == booking_data.room,
        Booking.start_time < end_dt,
        Booking.end_time > start_dt
    )

    results = session.exec(statement).all()

    if results:
        logger.warning(f"Booking conflict detected - Room: {booking_data.room}, Time: {start_dt}")
        raise HTTPException(status_code=409, detail="Booking conflict, room already booked for this time")

    # 11. Check user booking limit (max 5 bookings per day)
    booking_date = start_dt.date()
    day_start = datetime.combine(booking_date, datetime.min.time())
    day_end = datetime.combine(booking_date + timedelta(days=1), datetime.min.time())

    user_bookings_today = session.exec(
        select(Booking).where(
            Booking.user == booking_data.user,
            Booking.start_time >= day_start,
            Booking.start_time < day_end
        )
    ).all()

    if len(user_bookings_today) >= 5:
        logger.warning(f"User {booking_data.user} exceeded daily booking limit (5 bookings)")
        raise HTTPException(status_code=400, detail="User cannot have more than 5 bookings per day")

    # 12. Save the booking to database

    booking = Booking(
        room=booking_data.room,
        user=booking_data.user,
        start_time=start_dt,
        end_time=end_dt
    )

    session.add(booking)
    session.commit()
    session.refresh(booking)

    logger.info(f"Booking created successfully - ID: {booking.id}, Room: {booking.room}, User: {booking.user}, Time: {booking.start_time}")
    return booking 
    
        
    
@app.get(
    "/bookings",
    response_model=list[Booking],
    summary="Get bookings by room or user for a specific date",
    responses={
        200: {"description": "List of bookings retrieved successfully"},
        400: {"description": "Invalid query parameters"}
    }
)
def get_bookings(
    date: str,
    room: str | None = None,
    user: str | None = None,
    session: Session = Depends(get_session)
):
    """
    Retrieve all bookings for a specific room or user on a given date.

    **Query Parameters:**
    - **date**: Date in YYYY-MM-DD format (required)
    - **room**: Room name in MACRO_CASE (optional, but either room or user must be provided)
    - **user**: User's name (optional, but either room or user must be provided)

    **Important:** You must provide **exactly one** filter (either room OR user, not both).

    **Example Usage:**
    - Get bookings for EVEREST room on Dec 10: `GET /bookings?date=2025-12-10&room=EVEREST`
    - Get bookings for user john_doe on Dec 10: `GET /bookings?date=2025-12-10&user=john_doe`

    Returns an empty list if no bookings are found.
    """
    logger.info(f"Querying bookings - Date: {date}, Room: {room}, User: {user}")

    # 1. Validate that only one filter is provided
    if (room and user) or (not room and not user):
        logger.warning("Query rejected: Must provide exactly one filter (room or user)")
        raise HTTPException(status_code=400, detail="Provide exactly one filter, either room or user")
    
    # 2. Parse date string into a Python date
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    # 3. Validate room is in MACRO_CASE if provided
    if room and not room.isupper():
        raise HTTPException(status_code=400, detail="Room must be in MACRO_CASE")

    # 4. Build the query 
    
    if room:
        statement = select(Booking).where(
            Booking.room == room,
            Booking.start_time >= datetime.combine(date_obj, datetime.min.time()),
            Booking.start_time < datetime.combine(date_obj + timedelta(days=1), datetime.min.time())
        )
    else: 
        statement = select(Booking).where(
            Booking.user == user,
            Booking.start_time >= datetime.combine(date_obj, datetime.min.time()),
            Booking.start_time < datetime.combine(date_obj + timedelta(days=1), datetime.min.time())
        )
    
    results = session.exec(statement).all()
    logger.info(f"Query completed - Found {len(results)} booking(s)")
    return results


# This allows running the app directly with "python app.py"
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server via direct execution...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    ) 