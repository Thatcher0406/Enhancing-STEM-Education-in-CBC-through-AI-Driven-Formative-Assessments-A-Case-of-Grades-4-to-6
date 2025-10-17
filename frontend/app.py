# frontend/app.py

import streamlit as st
import requests
import os
import time
from urllib.parse import urlencode

# ==========================
#   Configuration
# ==========================
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_REDIRECT_URI = f"{BACKEND}/auth/google/callback"

# ==========================
#   Streamlit Setup
# ==========================
st.set_page_config(page_title="Adaptive Learning Auth", layout="centered", page_icon="🧠")

# ==========================
#   Custom CSS
# ==========================
def local_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }

        .main {
            background: linear-gradient(to bottom right, #dbeafe, #ede9fe);
            padding: 2rem;
        }

        h1, h2, h3, h4 {
            color: #2563eb;
            text-align: center;
        }

        .stCard {
            background-color: #ffffff;
            border-radius: 1.5rem;
            padding: 2rem;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            margin-top: 1.5rem;
            border: 3px solid #fef08a;
            transition: transform 0.3s ease;
        }

        .stCard:hover {
            transform: translateY(-4px);
        }

        .stButton>button {
            background: linear-gradient(to right, #22c55e, #16a34a);
            color: white;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            padding: 0.75rem 2rem;
            transition: all 0.3s ease;
        }

        .stButton>button:hover {
            background: linear-gradient(to right, #16a34a, #15803d);
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }

        input, textarea {
            border-radius: 8px !important;
            border: 2px solid #c7d2fe !important;
        }

        .success-box {
            background: #dcfce7;
            padding: 10px;
            border-radius: 8px;
            color: #166534;
            margin-top: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# ==========================
#   Handle Google OAuth Callback
# ==========================
params = st.query_params
if "oauth_token" in params:
    oauth_token = params["oauth_token"]
    st.session_state["token"] = oauth_token
    st.query_params.clear()
    st.success("🎉 Logged in with Google successfully!")

# ==========================
#   Registration Form
# ==========================
def register_parent():
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    st.header("👩‍👦 Parent Registration")
    full_name = st.text_input("Full name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        resp = requests.post(f"{BACKEND}/auth/register", json={
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "password": password,
            "confirm_password": confirm_password
        })
        if resp.status_code == 200:
            st.success("✅ Registered successfully! Please verify OTP sent to your email.")
        else:
            try:
                data = resp.json()
                st.error(f"❌ {data.get('detail', 'An unknown error occurred.')}")
            except ValueError:
                st.error("⚠️ Invalid response from backend.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================
#   Login (Email + OTP)
# ==========================
def login_flow():
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    st.header("🔐 Parent Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        resp = requests.post(f"{BACKEND}/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            st.info("📩 OTP sent to your email. Enter OTP below.")
            st.session_state["login_email_temp"] = email
            st.session_state["show_otp"] = True
        else:
            try:
                st.error(resp.json().get("detail", "Login failed"))
            except:
                st.error("Login failed")

    if st.session_state.get("show_otp"):
        otp = st.text_input("Enter OTP")
        if st.button("Verify OTP"):
            resp = requests.post(f"{BACKEND}/auth/verify-otp", params={
                "email": st.session_state["login_email_temp"],
                "otp": otp
            })
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                st.session_state["token"] = token
                st.success("🎉 Logged in successfully! Redirecting...")
                time.sleep(1.2)
                st.switch_page("pages/profile_select.py")
            else:
                try:
                    st.error(resp.json().get("detail", "Invalid OTP"))
                except:
                    st.error("Invalid OTP")
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================
#   Google OAuth Button
# ==========================
def google_login_button():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    st.markdown(
        f"""
        <div style="text-align:center; margin-top:20px;">
            <a href="{google_auth_url}" target="_self">
                <button style="
                    background-color:#4285F4;
                    color:white;
                    border:none;
                    padding:10px 20px;
                    font-size:16px;
                    border-radius:5px;
                    cursor:pointer;">
                    🌐 Continue with Google
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==========================
#   Child Profiles
# ==========================
def profiles_area():
    st.markdown("<div class='stCard'>", unsafe_allow_html=True)
    st.header("👧 Child Profiles")

    token = st.session_state.get("token")
    if not token:
        st.info("Please log in first to manage profiles.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    headers = {"Authorization": f"Bearer {token}"}
    name = st.text_input("Child name")
    grade = st.text_input("Grade")

    # Add Profile
    if st.button("Add Profile"):
        try:
            resp = requests.post(
                f"{BACKEND}/auth/profiles",
                json={"name": name, "grade": grade},
                headers=headers,
                timeout=10
            )
            if resp.status_code in [200, 201]:
                st.success("✅ Profile added successfully!")
            else:
                try:
                    error = resp.json().get("detail", "Error adding profile")
                except ValueError:
                    error = f"Server returned non-JSON response ({resp.status_code})"
                st.error(f"⚠️ {error}")
        except Exception as e:
            st.error(f"🚨 Connection error: {e}")

    # Fetch Profiles
    try:
        resp = requests.get(f"{BACKEND}/auth/profiles", headers=headers, timeout=10)
        if resp.status_code == 200:
            profiles = resp.json()
            if not profiles:
                st.info("No profiles yet. Add one above.")
            else:
                st.subheader("📋 Choose a profile")
                cols = st.columns(3)
                for i, p in enumerate(profiles):
                    with cols[i % 3]:
                        if st.button(f"Use {p['name']}", key=f"use_{p['id']}"):
                            st.session_state["active_profile"] = p
                            st.markdown(
                                f"<div class='success-box'>Active profile: <b>{p['name']}</b></div>",
                                unsafe_allow_html=True
                            )
        else:
            try:
                error = resp.json().get("detail", "Failed to load profiles.")
            except ValueError:
                error = f"Server returned non-JSON response ({resp.status_code})"
            st.error(f"⚠️ {error}")
    except Exception as e:
        st.error(f"🚨 Connection error while fetching profiles: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

# ==========================
#   Main UI
# ==========================
def main():
    st.markdown("<h1>🌈 STEM Kids Adaptive Learning Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:gray;'>Empowering Learning through Technology</p>", unsafe_allow_html=True)

    google_login_button()

    page = st.sidebar.radio("Navigate", ["Register", "Login", "Profiles"], index=0)
    if page == "Register":
        register_parent()
    elif page == "Login":
        login_flow()
    else:
        profiles_area()

# ==========================
#   Run App
# ==========================
if __name__ == "__main__":
    main()
