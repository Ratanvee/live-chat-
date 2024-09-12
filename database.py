from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import datetime

Base = declarative_base()

# ChatMessage model to store the message data
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, nullable=False)
    receiver = Column(String, nullable=True)  # Nullable if it's a broadcast
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Create the SQLite database
DATABASE_URL = "sqlite:///./chat.db"  # File-based SQLite database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the tables
Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./chat.db"  # Update with your database URL
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    receiver = Column(String, index=True, nullable=True)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
