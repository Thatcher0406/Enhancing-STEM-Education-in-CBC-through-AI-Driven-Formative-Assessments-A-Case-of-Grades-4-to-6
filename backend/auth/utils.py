# backend/auth/utils.py
import os
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import random
import string
from dotenv import load_dotenv
import os

load_dotenv() 
PWD_CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def hash_password(password: str) -> str:
    if len(password) > 72:
        password = password[:72]  # truncate safely
    return PWD_CTX.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return PWD_CTX.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))

def otp_expiry(minutes=10):
    return datetime.utcnow() + timedelta(minutes=minutes)
