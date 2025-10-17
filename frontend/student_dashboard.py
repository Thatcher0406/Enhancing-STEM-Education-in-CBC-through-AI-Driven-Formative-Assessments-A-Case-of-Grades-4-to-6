# frontend/student_dashboard.py
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Student Dashboard", layout="wide")

def main():
    # simulate profile info (in reality, pass via session_state or query param)
    profile = st.session_state.get("active_profile", {"name": "Alex", "grade": "5"})

    st.markdown(f"""
        <h2 style="text-align:center;">👋 Welcome back, {profile['name']}!</h2>
        <p style="text-align:center; color:gray;">Grade {profile['grade']} — {datetime.now().strftime('%B %Y')}</p>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("Your Learning Subjects")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
            <div style="background:#fff3cd; padding:30px; border-radius:20px; text-align:center;">
                <div style="font-size:50px;">🧮</div>
                <h3>Mathematics</h3>
                <p>⚠️ Needs more practice!</p>
                <a href="subject_page?subject=math">➡️ Go to Math</a>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div style="background:#e7f5ff; padding:30px; border-radius:20px; text-align:center;">
                <div style="font-size:50px;">📖</div>
                <h3>English</h3>
                <p>✅ Going great!</p>
                <a href="subject_page?subject=english">➡️ Go to English</a>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div style="background:#d3f9d8; padding:30px; border-radius:20px; text-align:center;">
                <div style="font-size:50px;">🔬</div>
                <h3>Integrated Science</h3>
                <p>⚠️ Needs more attention!</p>
                <a href="subject_page?subject=science">➡️ Go to Science</a>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
