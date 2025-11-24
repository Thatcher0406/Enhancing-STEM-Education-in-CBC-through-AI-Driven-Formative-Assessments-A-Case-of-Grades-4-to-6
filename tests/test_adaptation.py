# tests/test_adaptation.py
import pytest

# Adjust this import path to match your project layout
from backend.routes.quiz import choose_bloom, build_adaptive_context, BLOOM_LADDER


def make_history(
    *,
    attempt_count=1,
    last_score=None,
    last_bloom="Understand",
    avg_score=None,
    weak_spots=None,
    recent_attempts=None,
    avoid_stems=None,
):
    if avg_score is None:
        avg_score = last_score
    return {
        "attempt_count": attempt_count,
        "avg_score": avg_score,
        "last_bloom": last_bloom,
        "last_score": last_score,
        "recent_attempts": recent_attempts or [],
        "weak_spots": weak_spots or [],
        "avoid_stems": avoid_stems or [],
    }


# -----------------------------
# choose_bloom() unit tests
# -----------------------------

def test_choose_bloom_respects_requested_bloom():
    """If the UI/user specifies a Bloom level, history should be ignored."""
    history = make_history(last_score=0.3, last_bloom="Remember")
    result = choose_bloom(history, requested="Analyze")
    assert result == "Analyze"


def test_choose_bloom_first_attempt_defaults_to_understand():
    """With zero attempts, the system should start at 'Understand'."""
    history = {
        "attempt_count": 0,
        "avg_score": None,
        "last_bloom": None,
        "last_score": None,
        "recent_attempts": [],
        "weak_spots": [],
        "avoid_stems": [],
    }
    result = choose_bloom(history, requested=None)
    assert result == "Understand"


def test_choose_bloom_moves_up_on_high_score():
    """
    If last_score >= 0.85, Bloom should shift one step up the ladder,
    e.g. Understand -> Apply, Apply -> Analyze, etc.
    """
    history = make_history(last_score=0.90, last_bloom="Understand")
    result = choose_bloom(history, requested=None)
    # BLOOM_LADDER = ["Remember","Understand","Apply","Analyze","Evaluate","Create"]
    assert result == "Apply"


def test_choose_bloom_moves_down_on_low_score():
    """
    If last_score <= 0.5, Bloom should shift one step down the ladder,
    but not below 'Remember'.
    """
    history = make_history(last_score=0.40, last_bloom="Apply")
    result = choose_bloom(history, requested=None)
    assert result == "Understand"


def test_choose_bloom_uses_avg_for_mid_scores():
    """
    If 0.5 < last_score < 0.85 and avg_score >= 0.75,
    it should move at least to 'Apply'.
    """
    history = make_history(
        attempt_count=3,
        last_score=0.70,
        last_bloom="Understand",
        avg_score=0.80,
    )
    result = choose_bloom(history, requested=None)
    assert result == "Apply"


def test_choose_bloom_stays_same_for_mid_scores_and_low_avg():
    """
    If 0.5 < last_score < 0.85 and avg_score < 0.75,
    Bloom should stay at last_bloom.
    """
    history = make_history(
        attempt_count=3,
        last_score=0.70,
        last_bloom="Apply",
        avg_score=0.60,
    )
    result = choose_bloom(history, requested=None)
    assert result == "Apply"


def test_choose_bloom_never_goes_below_remember():
    history = make_history(last_score=0.20, last_bloom="Remember")
    result = choose_bloom(history, requested=None)
    assert result == "Remember"   # cannot go lower


def test_choose_bloom_never_goes_above_create():
    history = make_history(last_score=0.95, last_bloom="Create")
    result = choose_bloom(history, requested=None)
    assert result == "Create"     # cannot go higher


# -----------------------------
# build_adaptive_context() tests
# -----------------------------

def test_build_adaptive_context_first_attempt_narrative():
    history = {
        "attempt_count": 0,
        "avg_score": None,
        "last_bloom": None,
        "last_score": None,
        "recent_attempts": [],
        "weak_spots": [],
        "avoid_stems": [],
    }
    ctx = build_adaptive_context(history, bloom="Understand")
    assert "attempting this topic for the first time" in ctx["summary"]


def test_build_adaptive_context_includes_last_score_and_bloom():
    history = make_history(
        attempt_count=2,
        last_score=0.82,
        last_bloom="Apply",
        weak_spots=["Photosynthesis", "Plant cells"],
    )
    ctx = build_adaptive_context(history, bloom="Analyze")
    # Check summary mentions last score as a percentage
    assert "Last quiz score was 82%" in ctx["summary"]
    assert "Bloom level Apply" in ctx["summary"]
    # Should also mention weak spots in the narrative
    assert "Photosynthesis" in ctx["summary"]
    assert "weak_spots" in ctx and ctx["weak_spots"] == ["Photosynthesis", "Plant cells"]
