import os
from urllib.parse import urlencode
import requests
from fastapi.responses import RedirectResponse

# Google OAuth environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from datetime import datetime
from jose import jwt, JWTError
from ..database import SessionLocal
from .. import models, schemas
from ..email_sender import send_email
from .utils import (
    hash_password,
    verify_password,
    create_access_token,
    generate_otp,
    otp_expiry,
    SECRET_KEY,
    ALGORITHM,
)
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
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    existing = db.query(models.Parent).filter(models.Parent.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    parent = models.Parent(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)

    try:
        send_email(
            parent.email,
            "Welcome to STEM Kids",
            f"Hi {parent.full_name}, welcome to STEM Kids! You can now log in and verify via OTP."
        )
    except Exception:
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

    otp = generate_otp()
    parent.otp_secret = otp
    parent.otp_expires_at = otp_expiry()
    db.add(parent)
    db.commit()
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


# =========================================================
# =============== GOOGLE OAUTH2 AUTH FLOW =================
# =========================================================

@router.get("/google/login")
def google_login():
    """Return Google login URL."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google client ID not configured")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "access_type": "offline",
        "prompt": "select_account consent"
    }
    return {"auth_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)}


@router.get("/google/redirect")
def google_redirect():
    """Redirects user to Google OAuth authorization page."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google client ID not configured")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "access_type": "offline",
        "prompt": "select_account consent"
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@router.get("/google/callback")
def google_callback(code: str | None = None):
    """Handles Google OAuth callback and exchanges code for token."""
    if code is None:
        raise HTTPException(status_code=400, detail="Missing code from Google")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_resp = requests.post(token_url, data=data)
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    userinfo_resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    profile = userinfo_resp.json()
    email = profile.get("email")
    full_name = profile.get("name") or profile.get("given_name") or "Google User"

    db: Session = SessionLocal()
    parent = db.query(models.Parent).filter(models.Parent.email == email).first()
    if not parent:
        parent = models.Parent(
            full_name=full_name,
            email=email,
            phone=None,
            hashed_password=hash_password(os.urandom(12).hex()),
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)
    db.close()

    token_data = {"sub": str(parent.id), "role": "parent", "email": parent.email}
    jwt_token = create_access_token(token_data)

    redirect_url = f"{FRONTEND_URL}?oauth_token={jwt_token}"
    return RedirectResponse(redirect_url)
