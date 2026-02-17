# backend/routes/quiz.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os, requests, datetime, json
import re
from collections import Counter

from ..database import get_db
from .. import models

router = APIRouter(prefix="/quiz", tags=["quiz"])

QUIZ_ENGINE_URL = os.getenv("QUIZ_ENGINE_URL")
QUIZ_API_KEY = os.getenv("QUIZ_API_KEY")

class GeneratePayload(BaseModel):
    profile_id: int
    grade: int
    subject: str
    topic: str
    bloom_level: str | None = None  # "Auto" on frontend maps to None


class AnswerDetail(BaseModel):
    question_index: int
    stem: str
    options: list[str]
    picked_idx: int | None = None
    correct_idx: int | None = None
    explanation: str | None = None


class SubmitPayload(BaseModel):
    profile_id: int
    subject: str
    topic: str
    bloom_level: str | None = None
    score: float
    details: list[AnswerDetail] = []

# --------------------------
# Helpers (unchanged from before)
# --------------------------
def summarize_history(db: Session, profile_id: int, subject: str, topic: str) -> dict:
    """Gather the most recent attempts plus lightweight analytics for adaptation."""
    attempts = (
        db.query(models.QuizAttempt)
        .filter_by(child_id=profile_id, subject=subject, topic=topic)
        .order_by(models.QuizAttempt.taken_at.desc())
        .limit(3)
        .all()
    )
    if not attempts:
        return {
            "attempt_count": 0,
            "avg_score": None,
            "last_bloom": None,
            "last_score": None,
            "recent_attempts": [],
            "weak_spots": [],
            "avoid_stems": [],
        }

    attempt_ids = [a.id for a in attempts]
    details_map: dict[int, list[models.QuizAttemptDetail]] = {a.id: [] for a in attempts}
    if attempt_ids:
        details = (
            db.query(models.QuizAttemptDetail)
            .filter(models.QuizAttemptDetail.attempt_id.in_(attempt_ids))
            .all()
        )
        for d in details:
            details_map.setdefault(d.attempt_id, []).append(d)

    incorrect_counter: Counter[str] = Counter()
    recent_attempts = []
    avoid_stems: list[str] = []
    for idx, attempt in enumerate(attempts):
        details = details_map.get(attempt.id, [])
        wrong_stems = []
        question_stems = []
        for det in details:
            stem = det.stem or ""
            if stem:
                question_stems.append(stem)
            if det.picked_idx != det.correct_idx and stem:
                wrong_stems.append(stem)
                incorrect_counter[stem] += 1
        if idx == 0:
            avoid_stems = question_stems
        recent_attempts.append(
            {
                "id": attempt.id,
                "score": attempt.score,
                "bloom_level": attempt.bloom_level,
                "taken_at": attempt.taken_at.isoformat() if attempt.taken_at else None,
                "wrong_questions": wrong_stems,
            }
        )

    scored_values = [a.score for a in attempts if a.score is not None]
    avg_score = (sum(scored_values) / len(scored_values)) if scored_values else None
    weak_spots = [stem for stem, _ in incorrect_counter.most_common(5)]
    last_bloom = attempts[0].bloom_level if attempts else None
    last_score = attempts[0].score if attempts else None
    return {
        "attempt_count": len(attempts),
        "avg_score": avg_score,
        "last_bloom": last_bloom,
        "last_score": last_score,
        "recent_attempts": recent_attempts,
        "weak_spots": weak_spots,
        "avoid_stems": avoid_stems,
    }

BLOOM_LADDER = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

def _shift_bloom(current: str | None, delta: int) -> str:
    try:
        idx = BLOOM_LADDER.index(current or "")
    except ValueError:
        idx = BLOOM_LADDER.index("Understand")
    new_idx = max(0, min(len(BLOOM_LADDER) - 1, idx + delta))
    return BLOOM_LADDER[new_idx]

def choose_bloom(history: dict, requested: str | None) -> str:
    if requested:
        return requested
    attempts = history.get("attempt_count") or 0
    if attempts == 0:
        return "Understand"

    last_score = history.get("last_score") or 0
    last_bloom = history.get("last_bloom") or "Understand"
    if last_score >= 0.85:
        return _shift_bloom(last_bloom, 1)
    if last_score <= 0.5:
        return _shift_bloom(last_bloom, -1)

    avg = history.get("avg_score") or 0
    if avg >= 0.75:
        return max("Apply", last_bloom, key=lambda b: BLOOM_LADDER.index(b) if b in BLOOM_LADDER else 0)
    return last_bloom

def build_adaptive_context(history: dict, bloom: str) -> dict:
    weak_spots = history.get("weak_spots") or []
    attempt_count = history.get("attempt_count", 0)
    last_score = history.get("last_score")
    last_bloom = history.get("last_bloom")

    if attempt_count == 0:
        narrative = (
            "Learner is attempting this topic for the first time. Begin with foundational prompts "
            "and scaffold up gently."
        )
    else:
        pct = int((last_score or 0) * 100)
        narrative = f"Last quiz score was {pct}% at Bloom level {last_bloom}. "
        if weak_spots:
            narrative += (
                "Reinforce the concepts behind these missed questions: "
                + "; ".join(weak_spots[:3])
                + "."
            )
        else:
            narrative += "Learner answered almost everything correctly; introduce novel, multi-step reasoning."

    return {
        "summary": narrative,
        "weak_spots": weak_spots,
        "recent_attempts": history.get("recent_attempts", []),
        "avoid_repeats": history.get("avoid_stems", []),
        "recommended_bloom": bloom,
        "recommended_bloom_level": BLOOM_TEXT_TO_INT.get(bloom, BLOOM_TEXT_TO_INT["Understand"]),
    }

BLOOM_INT_TO_TEXT = {1:"Remember",2:"Understand",3:"Apply",4:"Analyze",5:"Evaluate",6:"Create"}
BLOOM_TEXT_TO_INT = {v:k for k,v in BLOOM_INT_TO_TEXT.items()}
LETTER_TO_IDX = {"A":0,"B":1,"C":2,"D":3}

def adapt_model_to_ui(model_payload: dict, requested_bloom: str | None = None) -> dict:
    meta = (model_payload or {}).get("metadata", {})
    bloom_level = meta.get("bloom_level")
    bloom_text = BLOOM_INT_TO_TEXT.get(bloom_level, bloom_level) if isinstance(bloom_level, int) else (bloom_level or "Understand")
    
    questions = (model_payload or {}).get("questions", [])
    ui_questions = []
    for i, q in enumerate(questions, start=1):
        opts = q.get("options", {})
        ordered = [opts.get("A",""), opts.get("B",""), opts.get("C",""), opts.get("D","")]
        ans_letter = (q.get("answer") or "").strip().upper()
        ui_questions.append({
            "id": f"q{i}",
            "stem": q.get("question","").strip(),
            "options": ordered,
            "answer_idx": LETTER_TO_IDX.get(ans_letter,0),
            "bloom": bloom_text,
            "explanation": q.get("rationale","").strip()
        })
    return {
        "metadata": {
            "subject": meta.get("subject"),
            "grade": meta.get("grade"),
            "topic": meta.get("topic"),
            "bloom_level": bloom_level,
            "bloom": bloom_text,
            "requested_bloom": requested_bloom or bloom_text,
        },
        "questions": ui_questions
    }

# --------------------------
# Forwarding endpoint
# --------------------------
@router.post("/generate")
def generate_quiz(p: GeneratePayload, db: Session = Depends(get_db)):
    if not QUIZ_ENGINE_URL:
        raise HTTPException(status_code=500, detail="Quiz engine URL not configured")

    history = summarize_history(db, p.profile_id, p.subject, p.topic)
    bloom = choose_bloom(history, p.bloom_level)
    adaptive_context = build_adaptive_context(history, bloom)

    # Ensure grade is sent as int to Colab quiz engine
    try:
        grade_int = int(re.sub(r"[^\d]", "", str(p.grade)))
    except:
        raise HTTPException(status_code=400, detail=f"Invalid grade format: {p.grade}")

    bloom_int = BLOOM_TEXT_TO_INT.get(bloom, BLOOM_TEXT_TO_INT["Understand"])

    colab_payload = {
        "grade": grade_int,
        "subject": p.subject,
        "topic": p.topic,
        "bloom_level": bloom_int,
        "bloom_label": bloom,
        "history": history,
        "adaptive_context": adaptive_context,
    }

    headers = {"X-API-Key": QUIZ_API_KEY} if QUIZ_API_KEY else {}
    try:
        # Forward request to Colab via Ngrok
        r = requests.post(f"{QUIZ_ENGINE_URL}/generate", json=colab_payload, headers=headers, timeout=1000)
        r.raise_for_status()
        raw = r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Quiz engine error: {e}")

    ui_payload = adapt_model_to_ui(raw, bloom)
    ui_payload["metadata"]["adaptive_context"] = adaptive_context
    ui_payload["metadata"]["history_snapshot"] = {
        "attempt_count": history.get("attempt_count"),
        "last_score": history.get("last_score"),
        "last_bloom": history.get("last_bloom"),
    }
    ui_payload["metadata"]["recommended_bloom_int"] = bloom_int
    ui_payload["metadata"]["recommended_bloom_text"] = bloom
    return ui_payload


@router.post("/submit")
def submit_quiz(p: SubmitPayload, db: Session = Depends(get_db)):
    """Persist a completed quiz attempt and per-question details."""
    # Create attempt summary row
    attempt = models.QuizAttempt(
        child_id=p.profile_id,
        subject=p.subject,
        topic=p.topic,
        bloom_level=p.bloom_level or "Unknown",
        score=p.score,
        taken_at=datetime.datetime.utcnow(),
    )
    db.add(attempt)
    db.flush()  # get attempt.id

    # Persist details if provided
    for d in (p.details or []):
        db.add(models.QuizAttemptDetail(
            attempt_id=attempt.id,
            question_index=d.question_index,
            stem=d.stem,
            options_json=json.dumps(d.options or []),
            picked_idx=d.picked_idx if d.picked_idx is not None else -1,
            correct_idx=d.correct_idx if d.correct_idx is not None else -1,
            explanation=d.explanation or "",
        ))

    db.commit()
    return {"attempt_id": attempt.id, "status": "saved"}


@router.get("/recent")
def recent_attempts(profile_id: int, subject: str | None = None, limit: int = 10, db: Session = Depends(get_db)):
    """Return recent quiz attempts for a profile, optionally filtered by subject."""
    q = db.query(models.QuizAttempt).filter(models.QuizAttempt.child_id == profile_id)
    if subject:
        q = q.filter(models.QuizAttempt.subject == subject)
    attempts = q.order_by(models.QuizAttempt.taken_at.desc()).limit(limit).all()
    return [
        {
            "id": a.id,
            "subject": a.subject,
            "topic": a.topic,
            "bloom_level": a.bloom_level,
            "score": a.score,
            "taken_at": a.taken_at.isoformat() if a.taken_at else None,
        }
        for a in attempts
    ]


@router.get("/attempt/{attempt_id}")
def get_attempt(attempt_id: int, db: Session = Depends(get_db)):
    a = db.query(models.QuizAttempt).filter(models.QuizAttempt.id == attempt_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Attempt not found")
    details = (
        db.query(models.QuizAttemptDetail)
        .filter(models.QuizAttemptDetail.attempt_id == attempt_id)
        .order_by(models.QuizAttemptDetail.question_index.asc())
        .all()
    )
    return {
        "id": a.id,
        "profile_id": a.child_id,
        "subject": a.subject,
        "topic": a.topic,
        "bloom_level": a.bloom_level,
        "score": a.score,
        "taken_at": a.taken_at.isoformat() if a.taken_at else None,
        "details": [
            {
                "question_index": d.question_index,
                "stem": d.stem,
                "options": json.loads(d.options_json or "[]"),
                "picked_idx": d.picked_idx,
                "correct_idx": d.correct_idx,
                "explanation": d.explanation or "",
            }
            for d in details
        ],
    }
