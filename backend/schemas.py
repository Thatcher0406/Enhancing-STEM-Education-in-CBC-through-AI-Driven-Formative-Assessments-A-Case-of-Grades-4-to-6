# backend/schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

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

class ChildCreate(BaseModel):
    name: str
    grade: Optional[str]

class ChildOut(BaseModel):
    id: int
    name: str
    grade: Optional[str]
    class Config:
        orm_mode = True
