# backend/schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# -------------------------------------------------------------
# PARENT AUTH SCHEMAS
# -------------------------------------------------------------
class ParentRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str]
    password: str
    confirm_password: str


class ParentLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------------------------------------------------------------
# CHILD PROFILE SCHEMAS
# -------------------------------------------------------------
class ChildProfileBase(BaseModel):
    name: str
    grade: Optional[str]


class ChildProfileCreate(ChildProfileBase):
    """Used when creating a new child profile"""
    pass


class ChildProfile(ChildProfileBase):
    """Used for returning full child profile info"""
    id: int
    parent_id: int

    class Config:
        orm_mode = True


# -------------------------------------------------------------
# CHILD SCHEMAS (for backwards compatibility if used elsewhere)
# -------------------------------------------------------------
class ChildCreate(BaseModel):
    name: str
    grade: Optional[str]


class ChildOut(BaseModel):
    id: int
    name: str
    grade: Optional[str]

    class Config:
        orm_mode = True
