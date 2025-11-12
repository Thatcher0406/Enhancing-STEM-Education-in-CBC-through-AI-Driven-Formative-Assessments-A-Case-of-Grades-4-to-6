import streamlit as st
import requests

BACKEND = st.secrets.get("BACKEND_URL", "http://localhost:8000")


def _update_query(profile, subject=None, grade=None, topic=None, review_attempt_id=None):
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


def _fetch_attempts(profile_id: int, subject: str | None = None, limit: int = 100):
    try:
        params = {"profile_id": profile_id, "limit": limit}
        if subject:
            params["subject"] = subject
        r = requests.get(f"{BACKEND}/quiz/recent", params=params, timeout=15)
        if r.status_code == 200:
            return r.json() or []
    except Exception:
        pass
    return []


def main():
    st.set_page_config(page_title="Previous Quizzes", layout="wide")

    prof = st.session_state.get("selected_profile")
    if not prof:
        st.warning("No profile selected. Go back and pick a profile.")
        st.stop()

    st.title("Previous Quizzes")

    preferred_subject = st.session_state.get("selected_subject")
    grade = st.session_state.get("selected_grade")

    # Build the subject list from attempts
    all_attempts = _fetch_attempts(prof["id"], subject=None, limit=200)
    subjects = sorted({a.get("subject") for a in all_attempts if a.get("subject")})
    if preferred_subject and preferred_subject not in subjects:
        subjects = [preferred_subject] + subjects

    if not subjects:
        st.info("No quizzes found yet.")
        if st.button("⬅️ Back to Subject"):
            _update_query(prof, preferred_subject, grade)
            st.switch_page("pages/subject_page.py")
        st.stop()

    # Subject filter
    default_idx = 0
    if preferred_subject and preferred_subject in subjects:
        default_idx = subjects.index(preferred_subject)
    subject = st.selectbox("Subject", subjects, index=default_idx)

    # Keep query params in sync so refresh/back preserves context
    _update_query(prof, subject, grade)

    # Fetch attempts for chosen subject
    attempts = _fetch_attempts(prof["id"], subject=subject, limit=100)

    st.markdown(f"### {subject}")
    if not attempts:
        st.caption("No previous quizzes for this subject yet.")
    else:
        for a in attempts:
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 3, 2])
            with col1:
                st.write(a.get("topic", ""))
            with col2:
                st.write(a.get("bloom_level", ""))
            with col3:
                score = int((a.get("score") or 0) * 100)
                st.write(f"{score}%")
            with col4:
                st.write(a.get("taken_at", ""))
            with col5:
                attempt_id = a.get("id")
                if st.button("Review", key=f"review_hist::{attempt_id}"):
                    st.session_state["review_attempt_id"] = attempt_id
                    st.session_state["selected_subject"] = subject
                    st.session_state["selected_topic"] = a.get("topic")
                    _update_query(prof, subject, grade, a.get("topic"), attempt_id)
                    st.switch_page("pages/quiz_page.py")

    st.markdown("---")
    if st.button("⬅️ Back to Subject"):
        st.session_state["selected_subject"] = subject
        _update_query(prof, subject, grade)
        st.switch_page("pages/subject_page.py")


if __name__ == "__main__":
    main()

