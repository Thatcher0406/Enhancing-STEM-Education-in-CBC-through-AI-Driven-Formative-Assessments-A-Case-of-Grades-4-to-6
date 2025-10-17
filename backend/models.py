# backend/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import datetime


# -------------------------------------------------------------
# PARENT MODEL
# -------------------------------------------------------------
class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    otp_secret = Column(String, nullable=True)       # Store last OTP or OTP token
    otp_expires_at = Column(DateTime, nullable=True) # OTP expiry time

    # Relationship to children
    children = relationship("ChildProfile", back_populates="parent", cascade="all, delete")


# -------------------------------------------------------------
# CHILD PROFILE MODEL
# -------------------------------------------------------------
class ChildProfile(Base):
    __tablename__ = "child_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"))

    # Relationship back to parent
    parent = relationship("Parent", back_populates="children")

children = relationship("ChildProfile", back_populates="parent", cascade="all, delete")
