#!/usr/bin/env python3
"""
auto_score_questions.py

Usage:
    python auto_score_questions.py questions_sample.csv

Output:
    questions_scored.csv (written to same folder)
"""

import os
import sys
import time
import json
import math
import argparse
from collections import defaultdict
from typing import Dict, Any

import pandas as pd

# Optional nice progress bar; if not installed, fallback to prints
try:
    from tqdm import tqdm
except Exception:
    tqdm = None

# OpenAI import
try:
    import openai
except Exception as e:
    raise RuntimeError(
        "OpenAI package not installed. Run: pip install openai"
    ) from e

# -------- CONFIG --------
MODEL = "gpt-4.1-mini"  # selected model
TEMPERATURE = 0.0       # deterministic scoring
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0    # seconds multiplier
OUTPUT_CSV = "questions_scored.csv"

# Scoring ranges
ALIGNMENT_RANGE = (0, 3)
SCALE_5_RANGE = (0, 5)  # clarity, grammar, cognitive_level, ambiguity

# -------- Helpers --------


def ensure_api_key():
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    if not key:
        raise RuntimeError(
            "OpenAI API key not found. Set environment variable OPENAI_API_KEY."
        )
    openai.api_key = key


def build_system_prompt() -> str:
    """
    System/instructional prompt to make the model return structured JSON
    with the requested scoring fields.
    """
    sys = (
        "You are an automated evaluator for primary-school multiple-choice "
        "questions. For each question (stem + context), return a JSON object "
        "with the following fields ONLY:\n\n"
        "cbc_code: string (human-readable code, e.g. 'Mathematics Grade 4 — Whole Numbers — Competency 01')\n"
        "alignment_rating: integer (0..3) where 3 means fully aligned to the topic/grade, 0 means misaligned\n"
        "clarity: integer (0..5) where 5 = crystal clear and unambiguous wording\n"
        "grammar: integer (0..5) where 5 = perfect grammar\n"
        "cognitive_level: integer (0..5) where 1 = very low cognitive demand (recall), 5 = very high (analysis/synthesis)\n"
        "ambiguity: integer (0..5) where 0 = no ambiguity, 5 = highly ambiguous\n"
        "notes: short string (explain any non-obvious decision briefly)\n\n"
        "Constraints and rules:\n"
        " - Return valid JSON only (no surrounding prose).\n"
        " - All numeric fields must be integers within the ranges specified.\n"
        " - Be conservative: when unsure, pick the lower numeric (safer) value.\n"
        " - Keep the 'notes' field short (<= 40 words).\n"
    )
    return sys


def build_user_prompt(row: Dict[str, Any], cbc_code: str) -> str:
    """
    Build the user prompt for a single question.
    row: dictionary with keys including 'subject','grade','topic','stem'
    cbc_code: the generated human-readable code for this question
    """
    stem = (row.get("stem") or "").strip()
    subject = row.get("subject", "")
    grade = row.get("grade", "")
    topic = row.get("topic", "")

    p = (
        f"Question stem: \"{stem}\"\n"
        f"Context: Subject={subject}; Grade={grade}; Topic={topic}\n"
        f"CBC code (proposed): {cbc_code}\n\n"
        "Evaluate how well this question matches the topic/grade and score it "
        "according to the rubric in the system prompt. Output a single JSON object."
    )
    return p


def call_openai_with_retries(prompt_system: str, prompt_user: str) -> Dict[str, Any]:
    """
    Call the OpenAI ChatCompletion API and parse JSON output.
    Retries on transient errors.
    """
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            # Use ChatCompletion API (chat format) so assistant role works consistently.
            resp = openai.ChatCompletion.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user},
                ],
                temperature=TEMPERATURE,
                max_tokens=400,
            )
            text = resp["choices"][0]["message"]["content"].strip()
            # Attempt to find first JSON substring if user returned extra text
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                json_text = text[json_start: json_end + 1]
            else:
                json_text = text

            parsed = json.loads(json_text)
            return parsed
        except (openai.error.RateLimitError, openai.error.ServiceUnavailableError) as e:
            attempt += 1
            wait = (RETRY_BACKOFF ** attempt)
            print(f"   !! transient API error: {e}. retry {attempt}/{MAX_RETRIES} after {wait:.1f}s")
            time.sleep(wait)
            continue
        except json.JSONDecodeError as e:
            # If we can't parse, return a minimal fallback
            attempt += 1
            print(f"   !! JSON parse error from model output. Attempt {attempt}/{MAX_RETRIES}. Raw output snippet: {text[:200]!r}")
            time.sleep(1.0 * attempt)
            continue
        except Exception as e:
            # Other exceptions: network, auth etc.
            attempt += 1
            print(f"   !! API call failed: {e}. Attempt {attempt}/{MAX_RETRIES}")
            time.sleep(1.0 * attempt)
            continue

    # If we get here, all retries failed: return minimal fallback
    return {
        "cbc_code": cbc_code,
        "alignment_rating": None,
        "clarity": None,
        "grammar": None,
        "cognitive_level": None,
        "ambiguity": None,
        "notes": "scoring_failed"
    }


def safe_int(value, low, high):
    try:
        v = int(value)
    except Exception:
        return None
    if v < low:
        return low
    if v > high:
        return high
    return v


# -------- Main flow --------
def auto_score(csv_path: str, output_path: str = OUTPUT_CSV):
    ensure_api_key()
    prompt_system = build_system_prompt()

    df = pd.read_csv(csv_path, dtype=str)
    # Ensure baseline columns exist
    for col in ["subject", "grade", "topic", "stem", "question_id"]:
        if col not in df.columns:
            df[col] = ""

    # Prepare CBC code counters per (subject, grade, topic)
    counters = defaultdict(int)

    results = []

    rows_iter = df.to_dict(orient="records")
    total = len(rows_iter)
    print(f"Loaded {total} rows from {csv_path}")

    iterator = tqdm(rows_iter) if tqdm else rows_iter

    idx = 0
    for row in iterator:
        idx += 1
        subject = (row.get("subject") or "Unknown").strip()
        grade = (row.get("grade") or "").strip()
        topic = (row.get("topic") or "").strip()
        stem_preview = (row.get("stem") or "").strip()[:80].replace("\n", " ")
        print(f"\n[{idx}/{total}] {subject} G{grade} [{topic}] — {stem_preview}")

        # create human-readable CBC code: "Mathematics Grade 4 — Whole Numbers — Competency 01"
        key = (subject, grade, topic)
        counters[key] += 1
        seq = counters[key]
        cbc_code = f"{subject} Grade {grade} — {topic} — Competency {seq:02d}"

        # build prompt and call model
        user_prompt = build_user_prompt(row, cbc_code)
        parsed = call_openai_with_retries(prompt_system, user_prompt)

        # Normalize and validate values
        alignment = safe_int(parsed.get("alignment_rating"), ALIGNMENT_RANGE[0], ALIGNMENT_RANGE[1])
        clarity = safe_int(parsed.get("clarity"), SCALE_5_RANGE[0], SCALE_5_RANGE[1])
        grammar = safe_int(parsed.get("grammar"), SCALE_5_RANGE[0], SCALE_5_RANGE[1])
        cognitive = safe_int(parsed.get("cognitive_level"), SCALE_5_RANGE[0], SCALE_5_RANGE[1])
        ambiguity = safe_int(parsed.get("ambiguity"), SCALE_5_RANGE[0], SCALE_5_RANGE[1])
        notes = parsed.get("notes") if isinstance(parsed.get("notes"), str) else ""

        out_row = dict(row)  # copy original fields
        out_row.update({
            "cbc_code": cbc_code,
            "alignment_rating": "" if alignment is None else int(alignment),
            "clarity": "" if clarity is None else int(clarity),
            "grammar": "" if grammar is None else int(grammar),
            "cognitive_level": "" if cognitive is None else int(cognitive),
            "ambiguity": "" if ambiguity is None else int(ambiguity),
            "auto_score_notes": notes,
        })

        results.append(out_row)
        # small delay to avoid hitting bursts (adjust as needed)
        time.sleep(0.35)

    # Save to CSV
    out_df = pd.DataFrame(results)
    out_df.to_csv(output_path, index=False)
    print(f"\n✅ Done. Wrote {len(out_df)} rows to {output_path}")


# CLI
def main_cli():
    parser = argparse.ArgumentParser(description="Auto-score questions using OpenAI")
    parser.add_argument("csv", help="path to input CSV (questions_sample.csv)")
    parser.add_argument("--out", "-o", default=OUTPUT_CSV, help="output CSV path")
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"Input file not found: {args.csv}")
        sys.exit(2)

    auto_score(args.csv, args.out)


if __name__ == "__main__":
    main_cli()
