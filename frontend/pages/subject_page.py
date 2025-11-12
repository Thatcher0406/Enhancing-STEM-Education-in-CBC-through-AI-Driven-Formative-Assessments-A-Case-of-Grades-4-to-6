# frontend/pages/subject_page.py
import streamlit as st
import random
import requests

BACKEND = st.secrets.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Subject Progress", layout="wide")

# ---- Context sync helpers ----
def _sync_from_query():
    qp = dict(st.query_params)
    # profile
    if "profile_id" in qp and "selected_profile" not in st.session_state:
        try:
            pid = int(qp.get("profile_id"))
        except Exception:
            pid = None
        st.session_state["selected_profile"] = {
            "id": pid,
            "name": qp.get("profile_name", "Student"),
            "grade": qp.get("profile_grade"),
        }
    # subject/grade/topic
    if "selected_subject" in qp and "selected_subject" not in st.session_state:
        st.session_state["selected_subject"] = qp.get("selected_subject")
    if "selected_grade" in qp and "selected_grade" not in st.session_state:
        st.session_state["selected_grade"] = qp.get("selected_grade")
    if "selected_topic" in qp and "selected_topic" not in st.session_state:
        st.session_state["selected_topic"] = qp.get("selected_topic")
    if "review_attempt_id" in qp and "review_attempt_id" not in st.session_state:
        try:
            st.session_state["review_attempt_id"] = int(qp.get("review_attempt_id"))
        except Exception:
            pass


def _sync_to_query(profile: dict | None, subject: str | None, grade: str | None, topic: str | None = None, review_attempt_id: int | None = None):
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
    if topic is not None:
        params["selected_topic"] = topic
    if review_attempt_id is not None:
        params["review_attempt_id"] = review_attempt_id
    else:
        params.pop("review_attempt_id", None)
    st.query_params.clear()
    st.query_params.update(params)

# ---------- TOPICS: keep the full production set here ----------
TOPICS = {
    "Grade 4": {
        "Mathematics": [
            "Numbers", "Whole Numbers", "Addition", "Subtraction", "Multiplication", "Division",
            "Fractions", "Decimals", "Measurement", "Length", "Area", "Mass", "Volume", "Capacity",
            "Time", "Money", "Geometry", "Angles", "Position and Direction", "2D-Shapes",
            "Algebra", "Data Handling"
        ],
        "English": [
            "The Family", "Family Celebrations", "Etiquette", "Accidents: First Aid", "Nutrition: Balanced Diet",
            "Internet: Email", "Technology: Cyber Safety", "The Farm", "HIV and AIDS",
            "Hygiene and Sanitation", "Sports: My Favourite Sport", "Clean Environment", "Money"
        ],
        "Science": [
            "Characteristics of Plants", "Animals", "Human Body", "Air Pollution", "Water Pollution",
            "Digital Devices", "Coding", "States of Matter", "Properties of Matter", "Forces and its Effects",
            "Energy", "Machines", "Earth and Space"
        ]
    },
    "Grade 5": {
        "Mathematics": [
            "Numbers – Whole Numbers", "Addition", "Subtraction", "Multiplication", "Division", "Fractions",
            "Decimals", "Measurement – Length", "Area", "Volume", "Capacity", "Mass", "Time", "Money",
            "Geometry – Lines – Angles", "3D Objects", "Data Representation", "Algebra – Simple Equations"
        ],
        "English": [
            "Child Rights and Responsibilities", "National Celebrations", "Etiquette Table Manners",
            "Road Accidents Prevention", "Traditional Food", "Jobs and Occupations",
            "Technology – Learning Through Technology", "The Farm – Cash Crops", "Leisure Time Activities",
            "Health – Communicable Diseases", "Sports – Appreciating Talents", "Environmental Pollution",
            "Money – Savings and Banking"
        ],
        "Science": [
            "Living Things", "Health Education: Diseases", "Environment", "Computing Devices: Handling Data",
            "Matter", "Force and Energy", "Earth and Space"
        ]
    },
    "Grade 6": {
        "Mathematics": [
            "Whole Numbers", "Multiplication", "Division", "Fractions", "Decimals", "Length", "Area",
            "Capacity", "Mass", "Time", "Money", "Lines", "Angles", "3D Objects", "Bar Graphs", "Inequalities"
        ],
        "English": [
            "Child Labour", "Cultural and Religious Celebrations", "Etiquette – Telephone",
            "Emergency Rescue Services", "Our Tourist Attraction", "Jobs and Occupations – Work Ethics",
            "Technology – Scientific Innovations", "The Farm – Animal Safety and Care", "Lifestyle – Diseases",
            "Proper Use of Leisure Time", "Sports – Indoor Games", "Environmental Conservation", "Money – Trade"
        ],
        "Science": [
            "Plants", "Animals", "Human Circulatory System", "Reproductive System", "Water Conservation",
            "Handling Data – Spreadsheets", "Properties of Matter", "Composition of Air", "Force",
            "Light Energy", "Machines"
        ]
    }
}

# ---------- helper: normalize subject and grade ----------
def normalize_subject(raw):
    if not raw:
        return "Mathematics"
    raw = str(raw).strip()
    m = raw.lower()
    if m in ("math", "mathematics"):
        return "Mathematics"
    if m in ("english",):
        return "English"
    if m in ("science", "integrated science", "integrated_science"):
        return "Science"
    # fallback: Title-case the token
    return raw.title()

def normalize_grade(raw_grade):
    # Accept "4", 4, "Grade 4", "grade 4" -> "Grade 4"
    if raw_grade is None:
        return None
    s = str(raw_grade).strip()
    if s.lower().startswith("grade"):
        return s.title()
    # if numeric
    if s.isdigit():
        return f"Grade {s}"
    # try to extract digit
    for token in s.split():
        if token.isdigit():
            return f"Grade {token}"
    return None

# ---------- main ----------
def main():
    # Restore context from URL if present
    _sync_from_query()
    # ensure profile present
    if "selected_profile" not in st.session_state:
        # user shouldn't be here; redirect back
        st.warning("No profile selected — redirecting to profile selection.")
        st.switch_page("pages/profile_select.py")
        return

    profile = st.session_state.get("selected_profile")
    # debug helpful values (hidden unless you set st.sidebar.checkbox)
    show_debug = st.sidebar.checkbox("Show debug values", value=False)

    # selected subject was set by the dashboard using st.session_state["selected_subject"]
    raw_subject = st.session_state.get("selected_subject", None)
    subject = normalize_subject(raw_subject)

    grade = normalize_grade(profile.get("grade"))
    if grade is None:
        # fallback if missing
        grade = "Grade 4"

    # debug info for dev
    if show_debug:
        st.sidebar.write("DEBUG ▶ raw_subject:", raw_subject)
        st.sidebar.write("DEBUG ▶ normalized subject:", subject)
        st.sidebar.write("DEBUG ▶ profile:", profile)
        st.sidebar.write("DEBUG ▶ normalized grade:", grade)

    # Keep URL params updated for refresh/back
    _sync_to_query(profile, subject, grade, st.session_state.get("selected_topic"), st.session_state.get("review_attempt_id"))

    st.title(f"{subject} - {grade}")
    st.markdown(f"### 👋 Welcome, {profile.get('name', 'Student')}!")

    # recent progress mock
    st.markdown("#### Your Recent Progress")
    prog_val = st.session_state.get("mock_progress", None)
    if prog_val is None:
        prog_val = random.uniform(0.45, 0.88)
        st.session_state["mock_progress"] = prog_val
    st.progress(prog_val)
    st.caption(f"Overall progress indicator: {int(prog_val*100)}%")

    # Determine topics using normalized keys
    topics = TOPICS.get(grade, {}).get(subject, [])
    if not topics:
        # Helpful message + debug
        st.warning("No topics found for this grade and subject.")
        if show_debug:
            st.info(f"Lookup keys used -> grade='{grade}', subject='{subject}'")
            st.write("Available grade keys:", list(TOPICS.keys()))
            st.write("Subjects for this grade (if grade exists):", list(TOPICS.get(grade, {}).keys()))
        return

    st.markdown("---")
    st.markdown("### Topics")
    if st.button("Previous Quizzes"):
        _sync_to_query(profile, subject, grade)
        st.switch_page("pages/quiz_history.py")
    st.markdown("### 📚 Topics")
    # Recent quiz history for this subject
    profile = st.session_state.get("selected_profile")
    raw_subject = st.session_state.get("selected_subject", None)
    # Normalize subject display name already used on this page
    try:
        if False and profile and raw_subject:
            resp = requests.get(
                f"{BACKEND}/quiz/recent",
                params={"profile_id": profile["id"], "subject": raw_subject, "limit": 5},
                timeout=10,
            )
            if resp.status_code == 200:
                attempts = resp.json() or []
                if attempts:
                    st.markdown("#### Recent Quiz History")
                    for a in attempts:
                        col1, col2, col3, col4 = st.columns([3,2,2,2])
                        with col1:
                            st.write(f"{a.get('topic')} — {a.get('bloom_level')}")
                        with col2:
                            st.write(f"Score: {int((a.get('score') or 0)*100)}%")
                        with col3:
                            st.write(a.get("taken_at", ""))
                        with col4:
                            if st.button("Review", key=f"review::{a.get('id')}"):
                                st.session_state["review_attempt_id"] = a.get("id")
                                st.switch_page("pages/quiz_page.py")
            else:
                st.caption("Could not load recent history.")
    except Exception:
        st.caption("Recent history unavailable.")
    st.info("Click a topic's Start button to open the quiz for that topic.")

    # layout topic cards with Start Quiz buttons
    cols = st.columns(3)
    for i, topic in enumerate(topics):
        with cols[i % 3]:
            # small status mock: needs attention if random < 0.35
            status_score = random.random()
            if status_score < 0.35:
                status_text = "⚠️ Needs practice"
                card_color = "#fff3cd"
            elif status_score < 0.75:
                status_text = "✨ Good progress"
                card_color = "#e7f5ff"
            else:
                status_text = "✅ Doing well"
                card_color = "#d3f9d8"

            st.markdown(
                f"""
                <div style="background:{card_color}; padding:18px; border-radius:12px; text-align:left; box-shadow:0 6px 14px rgba(0,0,0,0.06); margin-bottom:12px;">
                    <div style="font-size:18px; font-weight:600;">📘 {topic}</div>
                    <div style="color:gray; margin-top:6px;">{status_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Start Quiz button for this topic:
            btn_key = f"start_quiz::{subject}::{grade}::{topic}"
            if st.button("▶️ Start Quiz", key=btn_key):
                # save context for quiz page
                # ensure we do not land in review mode
                if "review_attempt_id" in st.session_state:
                    st.session_state.pop("review_attempt_id", None)
                st.session_state["selected_topic"] = topic
                st.session_state["selected_subject"] = subject
                st.session_state["selected_grade"] = grade
                st.success(f"Preparing quiz for '{topic}'...")
                # switch to quiz page when implemented (placeholder)
                _sync_to_query(profile, subject, grade, topic)
                st.switch_page("pages/quiz_page.py")

    st.markdown("---")
    st.subheader("📈 Recent Quiz History (sample)")
    st.empty()

    # back button
    if st.button("⬅️ Back to Dashboard"):
        st.switch_page("pages/student_dashboard.py")


if __name__ == "__main__":
    main()
