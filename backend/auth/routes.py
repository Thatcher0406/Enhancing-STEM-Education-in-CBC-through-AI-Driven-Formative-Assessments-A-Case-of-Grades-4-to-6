# backend/auth/routes.py

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from datetime import datetime
from jose import jwt, JWTError

from ..database import SessionLocal
from .. import models, schemas
from .utils import (
    hash_password,
    verify_password,
    create_access_token,
    generate_otp,
    otp_expiry,
    SECRET_KEY,
    ALGORITHM,
)
from ..email_sender import send_email

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------
#   Dependency: Get DB Session
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
#   Parent Registration
# ---------------------------
@router.post("/register", response_model=dict)
def register_parent(payload: schemas.ParentRegister, db: Session = Depends(get_db)):
    # Validate passwords
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    # Check if email already exists
    existing = db.query(models.Parent).filter(models.Parent.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new parent
    parent = models.Parent(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)

    # Send welcome email (optional)
    try:
        send_email(
            parent.email,
            "Welcome to STEM Kids",
            f"Hi {parent.full_name}, welcome to STEM Kids! You can now log in and verify via OTP."
        )
    except Exception:
        # Don’t fail registration if email sending fails
        pass

    return {"msg": "Registered successfully. Please log in and verify the OTP sent to your email."}


# ---------------------------
#   Parent Login (Generates OTP)
# ---------------------------
@router.post("/login", response_model=dict)
def login(payload: schemas.ParentLogin, db: Session = Depends(get_db)):
    parent = db.query(models.Parent).filter(models.Parent.email == payload.email).first()
    if not parent or not verify_password(payload.password, parent.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate OTP, save and send via email
    otp = generate_otp()
    parent.otp_secret = otp
    parent.otp_expires_at = otp_expiry()
    db.add(parent)
    db.commit()

    # Send OTP email
    try:
        send_email(
            parent.email,
            "Your Login OTP",
            f"Your OTP is: {otp}. It expires in 10 minutes."
        )
    except Exception:
        pass

    return {"msg": "OTP sent to your email. Verify it using /auth/verify-otp endpoint."}


# ---------------------------
#   Verify OTP (Generate JWT)
# ---------------------------
@router.post("/verify-otp", response_model=schemas.Token)
def verify_otp(email: str, otp: str, db: Session = Depends(get_db)):
    parent = db.query(models.Parent).filter(models.Parent.email == email).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    if not parent.otp_secret or parent.otp_secret != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if parent.otp_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    # Clear OTP after successful verification
    parent.otp_secret = None
    parent.otp_expires_at = None
    db.add(parent)
    db.commit()

    token = create_access_token({"sub": str(parent.id), "role": "parent", "email": parent.email})
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------
#   Helper: Get Current Parent
# ---------------------------
def get_current_parent(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        parent_id = int(payload.get("sub"))
    except (JWTError, ValueError, Exception):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    parent = db.query(models.Parent).get(parent_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    return parent


# ---------------------------
#   Parent Creates Child Profile
# ---------------------------
@router.post("/profiles", response_model=schemas.ChildOut)
def create_profile(
    payload: schemas.ChildCreate,
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    child = models.Child(parent_id=parent.id, name=payload.name, grade=payload.grade)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


# ---------------------------
#   List All Child Profiles
# ---------------------------
@router.get("/profiles", response_model=list[schemas.ChildOut])
def list_profiles(
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    return parent.children
