# frontend/app.py
import streamlit as st
import requests
import streamlit.components.v1 as components
import os

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Adaptive Learning Auth", layout="centered")

def register_parent():
    st.header("Parent Registration")
    full_name = st.text_input("Full name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Register"):
        resp = requests.post(f"{BACKEND}/auth/register", json={
            "full_name": full_name, "email": email, "phone": phone, "password": password, "confirm_password": confirm_password
        })
        if resp.status_code == 200:
            st.success("Registered. Please login and verify OTP sent to email.")
        else:
            try:
                data = resp.json()
                detail = data.get("detail", "An unknown error occurred.")
                st.error(f"❌ {detail}")
            except ValueError:
                st.error(f"⚠️ Invalid response from backend: {resp.text}")
                st.write("Status code:", resp.status_code)
                st.write("Raw response:", resp.text)
            #st.error(resp.json().get("detail") if resp.content else "Error")

def login_flow():
    st.header("Parent Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        resp = requests.post(f"{BACKEND}/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            st.info("OTP sent to email. Enter OTP below.")
            st.session_state["login_email_temp"] = email
            st.session_state["show_otp"] = True
        else:
            st.error(resp.json().get("detail"))

    if st.session_state.get("show_otp"):
        otp = st.text_input("Enter OTP")
        if st.button("Verify OTP"):
            resp = requests.post(f"{BACKEND}/auth/verify-otp", params={"email": st.session_state["login_email_temp"], "otp": otp})
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                st.session_state["token"] = token
                st.success("Logged in!")
            else:
                st.error(resp.json().get("detail"))

def profiles_area():
    st.header("Profiles")
    token = st.session_state.get("token")
    if not token:
        st.info("Please log in first")
        return
    headers = {"Authorization": f"Bearer {token}"}
    # create child
    name = st.text_input("Child name")
    grade = st.text_input("Grade")
    if st.button("Add Profile"):
        resp = requests.post(f"{BACKEND}/profiles", json={"name": name, "grade": grade}, headers=headers)
        if resp.status_code == 200 or resp.status_code == 201:
            st.success("Profile added")
        else:
            st.error(resp.json().get("detail"))

    # list profiles
    resp = requests.get(f"{BACKEND}/profiles", headers=headers)
    if resp.status_code == 200:
        profiles = resp.json()
        st.subheader("Choose a profile")
        cols = st.columns(3)
        for i, p in enumerate(profiles):
            with cols[i % 3]:
                if st.button(f"Use {p['name']}", key=f"use_{p['id']}"):
                    st.session_state["active_profile"] = p
                    st.success(f"Active profile: {p['name']}")

def main():
    st.title("Adaptive Learning — Auth demo")
    page = st.sidebar.selectbox("Page", ["Register", "Login", "Profiles"])
    if page == "Register":
        register_parent()
    elif page == "Login":
        login_flow()
    else:
        profiles_area()

if __name__ == "__main__":
    main()
