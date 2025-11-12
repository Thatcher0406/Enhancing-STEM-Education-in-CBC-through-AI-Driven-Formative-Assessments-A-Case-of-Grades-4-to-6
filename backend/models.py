# backend/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import datetime

#Quiz attempt model
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
import datetime

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"))  # adjust if your Profile model differs
    subject = Column(String)
    topic = Column(String)
    bloom_level = Column(String)
    score = Column(Float)
    taken_at = Column(DateTime, default=datetime.datetime.utcnow)


class QuizAttemptDetail(Base):
    __tablename__ = "quiz_attempt_details"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), index=True)
    question_index = Column(Integer)
    stem = Column(String)
    options_json = Column(String)  # JSON-encoded list of option strings
    picked_idx = Column(Integer)
    correct_idx = Column(Integer)
    explanation = Column(String)



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
