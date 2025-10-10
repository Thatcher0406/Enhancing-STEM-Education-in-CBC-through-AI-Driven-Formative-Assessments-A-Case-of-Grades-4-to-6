# backend/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class Parent(Base):
    __tablename__ = "parents"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    otp_secret = Column(String, nullable=True)  # store last OTP or OTP token
    otp_expires_at = Column(DateTime, nullable=True)

    children = relationship("Child", back_populates="parent")


class Child(Base):
    __tablename__ = "children"
    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"))
    name = Column(String, nullable=False)
    grade = Column(String, nullable=True)
    avatar = Column(String, nullable=True)  # optional

    parent = relationship("Parent", back_populates="children")
