from typing import Optional
from sqlmodel import SQLModel, Field 
from datetime import datetime 

# this create a SQL table called booking, id is the auto generated primary key
# room is the macro_case identifier, input by the user

class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room: str
    user: str
    start_time: datetime
    end_time: datetime 
    