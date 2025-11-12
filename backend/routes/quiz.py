# backend/routes/quiz.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os, requests, datetime, json
import re

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
    attempts = (
        db.query(models.QuizAttempt)
        .filter_by(child_id=profile_id, subject=subject, topic=topic)
        .order_by(models.QuizAttempt.taken_at.desc())
        .limit(5)
        .all()
    )
    if not attempts:
        return {"attempts": 0, "avg_score": None, "last_bloom": None}
    avg_score = sum(a.score for a in attempts) / len(attempts)
    last_bloom = attempts[0].bloom_level if attempts else None
    return {"attempts": len(attempts), "avg_score": avg_score, "last_bloom": last_bloom}

def choose_bloom(history: dict, requested: str | None) -> str:
    if requested:
        return requested
    if not history.get("attempts"):
        return "Understand"
    avg = history.get("avg_score") or 0
    if avg >= 0.8:
        return "Analyze"
    if avg >= 0.6:
        return "Apply"
    return "Remember"

BLOOM_INT_TO_TEXT = {1:"Remember",2:"Understand",3:"Apply",4:"Analyze",5:"Evaluate",6:"Create"}
LETTER_TO_IDX = {"A":0,"B":1,"C":2,"D":3}

def adapt_model_to_ui(model_payload: dict) -> dict:
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

    # Ensure grade is sent as int to Colab quiz engine
    try:
        grade_int = int(re.sub(r"[^\d]", "", str(p.grade)))
    except:
        raise HTTPException(status_code=400, detail=f"Invalid grade format: {p.grade}")

    colab_payload = {
        "grade": grade_int,
        "subject": p.subject,
        "topic": p.topic,
        "bloom_level": bloom,
        "history": history,
    }

    headers = {"X-API-Key": QUIZ_API_KEY} if QUIZ_API_KEY else {}
    try:
        # Forward request to Colab via Ngrok
        r = requests.post(f"{QUIZ_ENGINE_URL}/generate", json=colab_payload, headers=headers, timeout=1000)
        r.raise_for_status()
        raw = r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Quiz engine error: {e}")

    return adapt_model_to_ui(raw)


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
