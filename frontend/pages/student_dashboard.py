import streamlit as st
from datetime import datetime

from persistence import hydrate_persisted_state

st.set_page_config(page_title="Student Dashboard", layout="wide")
hydrate_persisted_state()


def _update_query(profile, subject=None, grade=None):
    params = dict(st.query_params)
    if profile:
        params["profile_id"] = profile.get("id")
        if profile.get("name") is not None:
            params["profile_name"] = profile.get("name")
        if profile.get("grade") is not None:
            params["profile_grade"] = profile.get("grade")
    if subject is not None:
        params["selected_subject"] = subject
    if grade is not None:
        params["selected_grade"] = grade
    st.query_params.clear()
    st.query_params.update(params)


def main():
    profile = st.session_state.get("selected_profile")

    if not profile:
        st.warning("No profile selected. Please go back to the profile selection page.")
        st.stop()

    st.markdown(
        f"""
        <h2 style="text-align:center;">👋 Welcome back, {profile['name']}!</h2>
        <p style="text-align:center; color:gray;">Grade {profile['grade']} — {datetime.now().strftime('%B %Y')}</p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("Your Learning Subjects")

    col1, col2, col3 = st.columns(3)

    # --- Math Card ---
    with col1:
        st.markdown(
            """
            <div style="background:#fff3cd; padding:30px; border-radius:20px; text-align:center;">
                <div style="font-size:50px;">🧮</div>
                <h3>Mathematics</h3>
                <p>⚠️ Needs more practice!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("➡️ Go to Math"):
            st.session_state["selected_subject"] = "Mathematics"
            _update_query(profile, "Mathematics", profile.get("grade"))
            st.switch_page("pages/subject_page.py")

    # --- English Card ---
    with col2:
        st.markdown(
            """
            <div style="background:#e7f5ff; padding:30px; border-radius:20px; text-align:center;">
                <div style="font-size:50px;">📖</div>
                <h3>English</h3>
                <p>✅ Going great!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("➡️ Go to English"):
            st.session_state["selected_subject"] = "English"
            _update_query(profile, "English", profile.get("grade"))
            st.switch_page("pages/subject_page.py")

    # --- Science Card ---
    with col3:
        st.markdown(
            """
            <div style="background:#d3f9d8; padding:30px; border-radius:20px; text-align:center;">
                <div style="font-size:50px;">🔬</div>
                <h3>Science</h3>
                <p>⚠️ Needs more attention!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("➡️ Go to Science"):
            st.session_state["selected_subject"] = "Science"
            _update_query(profile, "Science", profile.get("grade"))
            st.switch_page("pages/subject_page.py")


if __name__ == "__main__":
    main()
