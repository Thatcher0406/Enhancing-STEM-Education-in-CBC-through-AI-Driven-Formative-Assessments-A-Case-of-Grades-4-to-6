# frontend/profile_select.py
import streamlit as st
import requests
import random

# --- Backend URL ---
BACKEND = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# --- Page Setup ---
st.set_page_config(page_title="Choose Profile", layout="wide")

# --- Custom Styles ---
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

    .profile-card {
        background-color: #ffffff;
        border-radius: 1.5rem;
        padding: 1.5rem;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
        cursor: pointer;
        width: 180px;
        margin: 1rem auto;
        text-align: center;
    }

    .profile-card:hover {
        transform: translateY(-5px);
    }

    .stButton>button {
        background: linear-gradient(to right, #22c55e, #16a34a);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        background: linear-gradient(to right, #16a34a, #15803d);
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }
    </style>
""", unsafe_allow_html=True)

# --- Main App ---
def main():
    st.title("Who’s learning today? 📚")
    st.markdown("### Choose your profile or create a new one")

    # --- Verify Authentication ---
    token = st.session_state.get("token")
    if not token:
        st.warning("Please log in first to manage profiles.")
        return
    headers = {"Authorization": f"Bearer {token}"}

    # --- Add New Profile ---
    with st.expander("➕ Add New Profile"):
        name = st.text_input("Child name")
        grade = st.text_input("Grade (e.g., 4, 5, 6)")
        if st.button("Add Profile"):
            if not name or not grade:
                st.warning("Please fill in both name and grade.")
            else:
                resp = requests.post(f"{BACKEND}/auth/profiles",
                                     json={"name": name, "grade": grade},
                                     headers=headers)
                if resp.status_code in [200, 201]:
                    st.success("✅ Profile added successfully!")
                    st.rerun()
                else:
                    try:
                        st.error(resp.json().get("detail", "Error adding profile"))
                    except Exception:
                        st.error("Failed to add profile. Please check backend.")

    # --- Fetch Profiles ---
    resp = requests.get(f"{BACKEND}/auth/profiles", headers=headers)
    if resp.status_code == 200:
        profiles = resp.json()
        if profiles:
            cols = st.columns(3)
            for i, p in enumerate(profiles):
                with cols[i % 3]:
                    with st.container():
                        st.markdown(f"""
                            <div class="profile-card">
                                <div style="font-size:60px;">{random.choice(['🧒', '👧', '👦', '🧑‍🎓', '🎓'])}</div>
                                <div style="font-weight:bold;">{p['name']}</div>
                                <div style="color:gray;">Grade {p['grade']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Go as {p['name']}", key=f"profile_{p['id']}"):
                            st.session_state["selected_profile"] = p
                            st.switch_page("pages/student_dashboard.py")
        else:
            st.info("No profiles yet. Add one above to get started!")
    else:
        st.error("Failed to load profiles. Please try again.")

# --- Run App ---
if __name__ == "__main__":
    main()
