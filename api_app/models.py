from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime
from api_app.database import SessionLocal
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    email = Column(String, primary_key=True, unique=True)
    sub = Column(String)
    name = Column(String)
    picture = Column(String)
    space = Column(Integer, default=0)  # Current space used
    max_space = Column(BigInteger, default=2147483648)
    password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    uploads = relationship("Upload", back_populates="owner")  # Relationship to uploads
    # Defining the relationship with History
    history_entries = relationship("History", back_populates="user")


class Upload(Base):
    __tablename__ = "uploads"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String)
    path = Column(String)
    type = Column(String)  # Could be 'file' or 'folder'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    size = Column(Integer)
    owner_id = Column(String, ForeignKey("users.email"))
    owner = relationship("User", back_populates="uploads")

    shared_recipients = relationship("SharedRecipient", back_populates="upload")


class SharedUpload(Base):
    __tablename__ = "shared_uploads"
    id = Column(String, primary_key=True, default=generate_uuid)
    upload_id = Column(String, ForeignKey("uploads.id"))
    upload = relationship("Upload")  # Relationship to the upload
    time_shared = Column(DateTime, default=datetime.datetime.utcnow)
    permission = Column(String)  # e.g., 'read', 'write'
    description = Column(String)  # Description for sharing
    recipients = relationship(
        "SharedRecipient", back_populates="shared_upload"
    )  # Relationship to recipients


class SharedRecipient(Base):
    __tablename__ = "shared_recipients"
    id = Column(String, primary_key=True, default=generate_uuid)
    shared_upload_id = Column(String, ForeignKey("shared_uploads.id"))
    shared_upload = relationship("SharedUpload", back_populates="recipients")
    recipient_email = Column(String)
    upload_id = Column(
        String, ForeignKey("uploads.id")
    )  # Corrected foreign key relationship
    upload = relationship("Upload", back_populates="shared_recipients")


class History(Base):
    __tablename__ = "history"
    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    message = Column(String)

    # Defininig the relationship with User
    user_email = Column(String, ForeignKey("users.email"))
    user = relationship("User", back_populates="history_entries")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
