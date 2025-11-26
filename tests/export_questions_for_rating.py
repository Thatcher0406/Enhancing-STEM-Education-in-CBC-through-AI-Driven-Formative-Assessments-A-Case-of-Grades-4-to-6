"""
Generate a smaller CSV sample of quiz questions for manual review.

Changes from original:
- Only 5 topics per grade
- Only 2 Bloom levels
- Only 1 API call per combo
- Only 5 questions per combo
- Much faster (5–10 minutes)

Output: questions_sample.csv
"""

import requests
import pandas as pd
from typing import List, Dict, Any

# ===========================
# CONFIGURATION (LIGHT)
# ===========================

BASE_URL = "http://localhost:8000/quiz/generate"
PROFILE_ID = 1

# Only two bloom levels for speed
BLOOM_LEVELS = ["Remember", "Apply"]

# Only 1 call per combo
MAX_REQUESTS_PER_COMBO = 1

# Require only 5 questions per topic/grade/bloom
MIN_QUESTIONS_PER_COMBO = 5

# ===========================
# SMALL SCENARIOS — 5 TOPICS PER GRADE
# ===========================

SCENARIOS = [
    # ------------ GRADE 4 ------------
    {"subject": "Mathematics", "grade": 4, "topic": "Whole Numbers"},
    {"subject": "Mathematics", "grade": 4, "topic": "Addition"},
    {"subject": "Mathematics", "grade": 4, "topic": "Subtraction"},
    {"subject": "English",     "grade": 4, "topic": "The Family"},
    {"subject": "Science",     "grade": 4, "topic": "Animals"},

    # ------------ GRADE 5 ------------
    {"subject": "Mathematics", "grade": 5, "topic": "Whole Numbers"},
    {"subject": "Mathematics", "grade": 5, "topic": "Fractions"},
    {"subject": "English",     "grade": 5, "topic": "Child Rights And Responsibilities"},
    {"subject": "Science",     "grade": 5, "topic": "Diseases"},
    {"subject": "Science",     "grade": 5, "topic": "Properties Of Matter"},

    # ------------ GRADE 6 ------------
    {"subject": "Mathematics", "grade": 6, "topic": "Multiplication"},
    {"subject": "Mathematics", "grade": 6, "topic": "Fractions"},
    {"subject": "English",     "grade": 6, "topic": "Work Ethics"},
    {"subject": "Science",     "grade": 6, "topic": "Reproduction"},
    {"subject": "Science",     "grade": 6, "topic": "Forces"},
]


# ===========================
# FUNCTIONS
# ===========================

def call_backend(grade: int, subject: str, topic: str, bloom: str) -> Dict[str, Any]:
    """Call your FastAPI backend."""
    payload = {
        "profile_id": PROFILE_ID,
        "grade": grade,
        "subject": subject,
        "topic": topic,
        "bloom_level": bloom,
    }
    resp = requests.post(BASE_URL, json=payload, timeout=200)
    resp.raise_for_status()
    return resp.json()


def collect_questions(grade: int, subject: str, topic: str, bloom: str) -> List[Dict[str, Any]]:
    """One API call per combo, only unique stems."""
    print(f"→ {subject} G{grade} [{topic}] @ {bloom}")

    try:
        data = call_backend(grade, subject, topic, bloom)
    except Exception as e:
        print(f"   !! Backend error: {e}")
        return []

    questions = data.get("questions", [])
    if not questions:
        print("   !! No questions returned")
        return []

    seen = set()
    rows = []

    for q in questions:
        stem = (q.get("stem") or "").strip()
        if not stem or stem in seen:
            continue

        seen.add(stem)

        rows.append({
            "subject": subject,
            "grade": grade,
            "topic": topic,
            "bloom": bloom,
            "question_id": q.get("id", ""),
            "stem": stem,
            "cbc_code": "",
            "alignment_rating": "",
            "clarity": "",
            "grammar": "",
            "cognitive_level": "",
            "ambiguity": "",
        })

        if len(rows) >= MIN_QUESTIONS_PER_COMBO:
            break

    print(f"   ✔ collected {len(rows)} questions")
    return rows


# ===========================
# MAIN
# ===========================

def main():
    all_rows = []

    total = len(SCENARIOS) * len(BLOOM_LEVELS)
    print(f"Total combos: {total}")
    print("Generating...\n")

    combo_index = 0

    for sc in SCENARIOS:
        for bloom in BLOOM_LEVELS:
            combo_index += 1
            print(f"[{combo_index}/{total}]")
            rows = collect_questions(
                grade=sc["grade"],
                subject=sc["subject"],
                topic=sc["topic"],
                bloom=bloom,
            )
            all_rows.extend(rows)

    if not all_rows:
        print("No data collected — is backend running?")
        return

    df = pd.DataFrame(all_rows)
    df.to_csv("questions_sample.csv", index=False)

    print("\n===================================")
    print(f"✔ DONE — wrote {len(df)} rows to questions_sample.csv")
    print("===================================")


if __name__ == "__main__":
    main()
