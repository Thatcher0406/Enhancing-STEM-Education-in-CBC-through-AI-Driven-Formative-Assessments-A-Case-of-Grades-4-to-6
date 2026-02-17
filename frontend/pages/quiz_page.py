# frontend/pages/quiz_page.py
import streamlit as st
import requests
import json
import base64

from persistence import hydrate_persisted_state

BACKEND = st.secrets.get("BACKEND_URL", "http://localhost:8000")
hydrate_persisted_state()

def _encode_quiz_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"))
    token = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return token

def _decode_quiz_payload(token: str) -> dict | None:
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        return json.loads(raw)
    except Exception:
        return None

def _persist_quiz_state():
    quiz = st.session_state.get("current_quiz")
    if not quiz:
        return
    try:
        token = _encode_quiz_payload(quiz)
    except Exception:
        return
    params = dict(st.query_params)
    params["active_quiz"] = token
    st.query_params.clear()
    st.query_params.update(params)

def _restore_quiz_from_query():
    token = st.query_params.get("active_quiz")
    if not token or st.session_state.get("current_quiz"):
        return
    if isinstance(token, list):
        token = token[0]
    quiz = _decode_quiz_payload(token)
    if quiz:
        st.session_state["current_quiz"] = quiz

def _clear_persisted_quiz():
    st.session_state.pop("current_quiz", None)
    params = dict(st.query_params)
    if "active_quiz" in params:
        params.pop("active_quiz", None)
        st.query_params.clear()
        st.query_params.update(params)

# --- Context sync helpers ---
def _update_query(profile, subject, grade, topic=None, review_attempt_id=None):
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


def main():
    _restore_quiz_from_query()
    prof = st.session_state.get("selected_profile")
    grade = st.session_state.get("selected_grade")
    # Convert to number
    if isinstance(grade, str) and "Grade" in grade:
        grade = int(grade.replace("Grade", "").strip())
    subject = st.session_state.get("selected_subject")
    topic = st.session_state.get("selected_topic")

    if not all([prof, grade, subject, topic]):
        st.warning("Missing context. Go back and pick a topic.")
        st.stop()

    st.title(f"{subject} - {topic}")

    # Review mode: if coming from history, display saved attempt details
    review_attempt_id = st.session_state.get("review_attempt_id")
    if review_attempt_id:
        try:
            r = requests.get(f"{BACKEND}/quiz/attempt/{review_attempt_id}", timeout=20)
            if r.status_code == 200:
                data = r.json()
                st.subheader("Quiz Review")
                st.caption(f"Taken at: {data.get('taken_at')} | Bloom: {data.get('bloom_level')}")
                st.success(f"Score: {int((data.get('score') or 0)*100)}%")
                for i, d in enumerate(data.get("details", []), start=1):
                    stem = d.get("stem", "")
                    options = d.get("options", [])
                    picked = d.get("picked_idx")
                    correct = d.get("correct_idx")
                    explanation = d.get("explanation", "")
                    st.markdown(f"**Q{i}. {stem}**")
                    if picked == correct:
                        st.success("Your answer was correct.")
                    else:
                        st.error("Your answer was incorrect.")
                    if 0 <= correct < len(options):
                        st.write(f"Correct answer: {options[correct]}")
                    if 0 <= (picked or -1) < len(options):
                        st.write(f"Your answer: {options[picked]}")
                    if explanation:
                        st.info(f"Why: {explanation}")
                    st.divider()
            else:
                st.warning("Could not load attempt details.")
        except Exception as e:
            st.warning(f"Error loading attempt: {e}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Subject"):
                _clear_persisted_quiz()
                st.session_state.pop("review_attempt_id", None)
                st.switch_page("pages/subject_page.py")
        with col2:
            if st.button("New Quiz on this Topic"):
                _clear_persisted_quiz()
                st.session_state.pop("review_attempt_id", None)
        st.stop()

    # Clear persisted quiz if it belongs to another topic/subject
    existing_quiz = st.session_state.get("current_quiz")
    if existing_quiz:
        meta = existing_quiz.get("metadata", {}) or {}
        if meta.get("subject") != subject or meta.get("topic") != topic:
            _clear_persisted_quiz()

    bloom_choice = st.selectbox(
        "Bloom level",
        ["Auto", "Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"],
        index=0,
    )

    if st.button("Generate Questions"):
        payload = {
            "profile_id": prof["id"],
            "grade": grade,
            "subject": subject,
            "topic": topic,
            "bloom_level": None if bloom_choice == "Auto" else bloom_choice,
        }
        try:
            resp = requests.post(f"{BACKEND}/quiz/generate", json=payload, timeout=900)
            resp.raise_for_status()
            st.session_state["current_quiz"] = resp.json()
            _persist_quiz_state()
        except Exception as e:
            st.error(f"Failed to generate quiz: {e}")

    quiz = st.session_state.get("current_quiz")
    if quiz:
        metadata = quiz.get("metadata", {}) or {}
        bloom = metadata.get("bloom") or metadata.get("requested_bloom")
        requested_bloom = metadata.get("requested_bloom")
        adaptive_context = metadata.get("adaptive_context") or {}
        history_snapshot = metadata.get("history_snapshot") or {}

        if bloom:
            if requested_bloom and requested_bloom != bloom:
                st.markdown(f"**Bloom level:** {bloom} _(requested {requested_bloom})_")
            else:
                st.markdown(f"**Bloom level:** {bloom}")
        # Adaptive context is sent to backend/model only; avoid exposing remediation text to learners
        questions = quiz.get("questions", [])
        for i, q in enumerate(questions, start=1):
            st.markdown(f"**Q{i}. {q['stem']}**")
            st.radio("Choose:", q["options"], key=f"q_{i}")
            st.divider()

        if st.button("Submit"):
            correct = 0
            details = []
            for i, q in enumerate(questions, start=1):
                picked = st.session_state.get(f"q_{i}")
                if picked is None:
                    continue
                try:
                    picked_idx = q["options"].index(picked)
                except ValueError:
                    picked_idx = -1
                if picked_idx == q.get("answer_idx"):
                    correct += 1

                details.append({
                    "question_index": i,
                    "stem": q.get("stem", ""),
                    "options": q.get("options", []),
                    "picked_idx": picked_idx,
                    "correct_idx": q.get("answer_idx"),
                    "explanation": q.get("explanation", ""),
                })

            total = max(1, len(questions))
            score = correct / total
            st.success(f"Score: {correct}/{total} ({int(score*100)}%)")

            # Show per-question feedback with correct answer and rationale
            st.subheader("Answers and Explanations")
            for i, q in enumerate(questions, start=1):
                picked = st.session_state.get(f"q_{i}")
                try:
                    picked_idx = q["options"].index(picked) if picked is not None else -1
                except ValueError:
                    picked_idx = -1
                correct_idx = q.get("answer_idx")
                stem = q.get("stem", "")
                st.markdown(f"**Q{i}. {stem}**")
                if picked_idx == correct_idx:
                    st.success("Correct")
                else:
                    st.error("Incorrect")
                if 0 <= correct_idx < len(q["options"]):
                    st.write(f"Correct answer: {q['options'][correct_idx]}")
                if 0 <= picked_idx < len(q["options"]):
                    st.write(f"Your answer: {q['options'][picked_idx]}")
                rationale = q.get("explanation") or q.get("rationale") or ""
                if rationale:
                    st.info(f"Why: {rationale}")
                st.divider()

            try:
                resp = requests.post(
                    f"{BACKEND}/quiz/submit",
                    json={
                        "profile_id": prof["id"],
                        "subject": subject,
                        "topic": topic,
                        "bloom_level": metadata.get("bloom") or metadata.get("requested_bloom") or "Unknown",
                        "score": score,
                        "details": details,
                    },
                    timeout=15,
                )
                if resp.status_code not in (200, 201):
                    st.warning("Saved locally; backend submit failed.")
            except Exception as e:
                st.warning(f"Saved locally; submit error: {e}")


if __name__ == "__main__":
    main()
