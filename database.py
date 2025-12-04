from sqlmodel import SQLModel, create_engine, Session 

# this creates a file called bookings.db in this folder 
DATABASE_URL = "sqlite:///./bookings.db"

# engine is the connection to the database, echo=True, means logs SQL queries
engine = create_engine(DATABASE_URL, echo=True)

#  turns all the SQLModel classes into real SQL tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# important for FastAPI dependancy injection, any endpoint needing DB will call, this makes the DB access very clean 
def get_session():
    with Session(engine) as session:
        yield session 