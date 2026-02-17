# backend/main.py
import dotenv; dotenv.load_dotenv()

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import requests
import os


from .database import engine, Base
from .auth import routes as auth_routes
from . import models

# ==========================
#   Initialize Database
# ==========================
Base.metadata.create_all(bind=engine)

# ==========================
#   Create FastAPI App
# ==========================
app = FastAPI(title="Adaptive Learning Auth")

# ==========================
#   CORS Configuration
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Restrict in production (use your frontend domain)
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
#   Include Auth Routes
# ==========================
app.include_router(auth_routes.router)

# ==========================
#   Include Quiz Routes
# ==========================
from .routes import quiz as quiz_routes
app.include_router(quiz_routes.router)



# ==========================
#   Google OAuth Callback
# ==========================
@app.get("/auth/google/callback_localdebug")
def google_callback(code: str):
    """
    Handles the Google OAuth callback:
    Exchanges the authorization code for tokens,
    fetches the user's Google profile, and returns both.
    """
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }

    # Exchange code for access & refresh tokens
    r = requests.post(token_url, data=data)
    token_response = r.json()

    # Fetch user profile using access token
    access_token = token_response.get("access_token")
    user_info = {}

    if access_token:
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

    # ✅ Optionally: handle user registration/login here (save to DB)
    # Example:
    # save_user_if_not_exists(user_info)

    return {
        "token_response": token_response,
        "user_info": user_info
    }


# ==========================
#   Root Route (Optional)
# ==========================
@app.get("/")
def home():
    return {"message": "Welcome to the Adaptive Learning Auth API 🚀"}


@app.get("/debug-env")
def debug_env():
    return {
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "GOOGLE_REDIRECT_URI": os.getenv("GOOGLE_REDIRECT_URI")
    }
