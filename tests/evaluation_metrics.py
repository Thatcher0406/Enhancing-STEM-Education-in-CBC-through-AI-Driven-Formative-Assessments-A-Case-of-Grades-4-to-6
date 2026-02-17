# evaluation_metrics.py
import pandas as pd


# -------------------------------
# METRIC 1 — Question Relevance
# (CBC Alignment)
# -------------------------------

def compute_cbc_alignment(df: pd.DataFrame) -> dict:
    """
    Expects a column 'alignment_rating' with values 1, 2, or 3.

    3 = fully aligned
    2 = partially aligned
    1 = not aligned
    """
    if "alignment_rating" not in df.columns:
        raise ValueError("DataFrame must contain 'alignment_rating' column")

    total_questions = len(df)
    if total_questions == 0:
        return {"alignment_score_pct": 0.0, "total_questions": 0}

    fully_aligned = (df["alignment_rating"] == 3).sum()
    alignment_score = (fully_aligned / total_questions) * 100.0

    return {
        "alignment_score_pct": alignment_score,
        "total_questions": int(total_questions),
        "fully_aligned_count": int(fully_aligned),
    }


# -------------------------------
# METRIC 3 — Question Quality
# -------------------------------

QUALITY_COLUMNS = ["clarity", "grammar", "cognitive_level", "ambiguity"]


def compute_question_quality(df: pd.DataFrame) -> dict:
    """
    Expects columns:
      - clarity
      - grammar
      - cognitive_level
      - ambiguity
    each rated 1–5.
    """
    for col in QUALITY_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"DataFrame must contain '{col}' column")

    # Per-question average quality score (1–5)
    df["quality_avg"] = df[QUALITY_COLUMNS].mean(axis=1)

    overall_avg = df["quality_avg"].mean()

    # Also compute per-dimension averages (optional, nice for the report)
    per_dimension = {col: df[col].mean() for col in QUALITY_COLUMNS}

    return {
        "overall_quality_avg": float(overall_avg),
        "per_dimension_avg": {k: float(v) for k, v in per_dimension.items()},
        "total_questions": int(len(df)),
    }


# -------------------------------
# Convenience helper
# -------------------------------

def load_and_evaluate(csv_path: str) -> dict:
    """
    Simple helper: load your ratings CSV and compute both metrics.
    """
    df = pd.read_csv(csv_path)

    cbc = compute_cbc_alignment(df)
    quality = compute_question_quality(df)

    return {
        "cbc_alignment": cbc,
        "question_quality": quality,
    }


if __name__ == "__main__":
    # Example usage from CLI:
    import sys

    if len(sys.argv) != 2:
        print("Usage: python evaluation_metrics.py path/to/ratings.csv")
        raise SystemExit(1)

    csv_path = sys.argv[1]
    metrics = load_and_evaluate(csv_path)

    print("\n=== METRIC 1: CBC Alignment ===")
    print(f"Total questions: {metrics['cbc_alignment']['total_questions']}")
    print(f"Fully aligned (score=3): {metrics['cbc_alignment']['fully_aligned_count']}")
    print(f"Alignment score: {metrics['cbc_alignment']['alignment_score_pct']:.2f}%")

    print("\n=== METRIC 3: Question Quality ===")
    print(f"Total questions: {metrics['question_quality']['total_questions']}")
    print(f"Overall quality average: {metrics['question_quality']['overall_quality_avg']:.2f}/5")

    print("\nPer-dimension averages:")
    for k, v in metrics["question_quality"]["per_dimension_avg"].items():
        print(f" - {k}: {v:.2f}/5")
