"""Ordering: how cards are ranked and why. No network, no aiohttp."""

from __future__ import annotations

FRESH_MAX = 6
STAKES_BASE = {"revenue": 4.0, "product": 2.0, "personal": 1.0}
DEFAULT_STAKES = "personal"
BLOCKED_MULTIPLIER = 1.4
PARKED_MULTIPLIER = 0.2


def urgency(days_to_target: int | None) -> float:
    """Multiplier derived from how close the target date is."""
    if days_to_target is None:
        return 1.0
    if days_to_target < 0:
        return 3.0
    if days_to_target <= 30:
        return 2.4
    if days_to_target <= 90:
        return 1.7
    if days_to_target <= 180:
        return 1.3
    return 1.0


def target_phrase(days_to_target: int | None) -> str:
    """Short label for how close a target is. Shown as scoring evidence."""
    if days_to_target is None:
        return "no target"
    if days_to_target < 0:
        overdue = -days_to_target
        unit = f"{overdue}d" if overdue < 60 else f"{round(overdue / 30)}mo"
        return f"{unit} overdue"
    if days_to_target == 0:
        return "due today"
    unit = (
        f"{days_to_target}d"
        if days_to_target < 60
        else f"{round(days_to_target / 30)}mo"
    )
    return f"{unit} left"


def score_factors(
    stakes: str, days_to_target: int | None, blocker: str, phase: str
) -> list[dict]:
    """The multipliers behind a score, labelled, in the order applied.

    This is the single source of the arithmetic — `compute_score` multiplies
    exactly these, so the reasoning shown on a card can never disagree with
    the number it sorted by.
    """
    factors = [
        {
            "label": stakes,
            "factor": STAKES_BASE.get(stakes, STAKES_BASE[DEFAULT_STAKES]),
        },
        {"label": target_phrase(days_to_target), "factor": urgency(days_to_target)},
    ]
    if blocker:
        factors.append({"label": "blocked", "factor": BLOCKED_MULTIPLIER})
    if phase == "parked":
        factors.append({"label": "parked", "factor": PARKED_MULTIPLIER})
    return factors


def compute_score(
    stakes: str, days_to_target: int | None, blocker: str, phase: str
) -> float:
    """Priority score. Never stored — always computed from current facts."""
    score = 1.0
    for factor in score_factors(stakes, days_to_target, blocker, phase):
        score *= factor["factor"]
    return round(score, 2)


def band(score: float) -> str:
    if score >= 4.0:
        return "high"
    if score >= 2.0:
        return "normal"
    return "low"


def classify(blocker: str, phase: str, age: int | None, stale_days: int) -> str:
    if blocker:
        return "blocked"
    if phase == "parked":
        return "parked"
    if age is None:
        return "unknown"
    if age <= FRESH_MAX:
        return "fresh"
    if age <= stale_days:
        return "aging"
    return "stale"


def sort_cards(cards: list[dict]) -> list[dict]:
    """Descending by score, then descending by age."""
    return sorted(
        cards,
        key=lambda c: (
            -c["score"],
            -(c["age"] if c["age"] is not None else -1),
        ),
    )
