"""Ordering: how cards are ranked and why. No network, no aiohttp."""

from __future__ import annotations

import datetime

FRESH_MAX = 6
MOMENTUM_RECENT_DAYS = 7
MOMENTUM_WINDOW_DAYS = 30
RECENT_WEIGHT = 3


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


URGENT_DAYS = 30
STALL_FLOOR = 3
BLOCKED_DEBT = 1.5
OVERDUE_DEBT = 2.0
STAKES_ORDER = {"revenue": 0, "product": 1, "personal": 2}


def momentum(c7: int | None, c30: int | None) -> int | None:
    """Weighted commit activity. None means unknown, which is not zero."""
    if c7 is None or c30 is None:
        return None
    return c7 * RECENT_WEIGHT + c30


def debt(
    age: int | None, stale_days: int, blocker: str, days_to_target: int | None
) -> float:
    """How much this project is owed. Marks a card; never moves it."""
    total = 0.0
    if age is not None and stale_days:
        total += age / stale_days
    if blocker:
        total += BLOCKED_DEBT
    if days_to_target is not None and days_to_target < 0:
        total += OVERDUE_DEBT
    return round(total, 2)


def quiet_span(age: int | None, floor: bool = False) -> str:
    """How long this project has been quiet, as a phrase.

    `floor` means the age is a lower bound, not a measurement: STATE.md-only
    commits have been excluded and no real work appears anywhere in the
    30-day window, so all that is honestly known is "at least this long".
    """
    if age is None:
        return ""
    return f"{age}+ days" if floor else f"{age} days"


def debt_reason(
    age: int | None,
    stale_days: int,
    blocker: str,
    days_to_target: int | None,
    floor: bool = False,
) -> str:
    """Four words on why this card is owed attention."""
    if blocker:
        return "blocked"
    if days_to_target is not None and days_to_target < 0:
        return f"{-days_to_target}d overdue"
    span = quiet_span(age, floor)
    return f"quiet {span}" if span else ""


def order_key(card: dict) -> tuple:
    """Deadline tier first, then momentum descending, then stakes."""
    dtt = card.get("days_to_target")
    urgent = dtt is not None and dtt <= URGENT_DAYS
    mom = card.get("momentum")
    return (
        0 if urgent else 1,
        dtt if urgent else 0,
        -(mom if mom is not None else 0),
        STAKES_ORDER.get(card.get("stakes"), 9),
        card.get("repo", ""),
    )


def _hero_is_worth_showing(card: dict) -> bool:
    """A hero needs something to say. Unknown momentum still counts."""
    dtt = card.get("days_to_target")
    if card.get("next"):
        return True
    if dtt is not None and dtt <= URGENT_DAYS:
        return True
    return card.get("momentum") != 0


def stall(card: dict) -> int | None:
    """Commits this project was walked away from. None when unknown.

    Absence of work is not debt; work that stopped is. A project with thirty
    commits and then silence has thirty commits of loaded context sitting
    there, and the size of that abandonment is the urgency. A project that has
    simply been asleep all month has nothing at stake and is not stalled.
    """
    c7 = card.get("commits_7d")
    c30 = card.get("commits_30d")
    if c7 is None or c30 is None:
        return None
    if c7 == 0 and c30 >= STALL_FLOOR:
        return c30
    return 0


def _rescue_eligible(card: dict, hero: dict | None) -> bool:
    """A rescue must be stalled, actionable, and not already on screen."""
    if card is hero:
        return False
    if card.get("phase") == "parked":
        return False
    # A blocker is not fixed by working harder, and the card already renders
    # it prominently.
    if card.get("blocker"):
        return False
    # Deadline-tier cards are at the top of the board already. Rescuing one is
    # shouting at something being looked at.
    dtt = card.get("days_to_target")
    if dtt is not None and dtt <= URGENT_DAYS:
        return False
    return bool(stall(card))


def assign_roles(ordered: list[dict]) -> None:
    """Set `role` on each card. Mutates in place; `ordered` must be sorted."""
    for card in ordered:
        card["role"] = "tail"
    if not ordered:
        return
    hero = None
    if _hero_is_worth_showing(ordered[0]):
        ordered[0]["role"] = "hero"
        hero = ordered[0]

    candidates = [c for c in ordered if _rescue_eligible(c, hero)]
    if candidates:
        # Biggest abandonment first; ties go to the warmer stall, which is
        # cheaper to restart and likelier to actually happen.
        best = min(
            candidates,
            key=lambda c: (
                -stall(c),
                c.get("age") if c.get("age") is not None else 10**6,
                STAKES_ORDER.get(c.get("stakes"), 9),
                c.get("repo", ""),
            ),
        )
        best["role"] = "rescue"


def stall_reason(card: dict) -> str:
    """What this card walked away from, and how long ago. Empty when none."""
    walked = stall(card)
    if not walked:
        return ""
    age = card.get("age")
    span = quiet_span(age, card.get("age_is_floor", False))
    unit = "commit" if walked == 1 else "commits"
    if not span:
        return f"{walked} {unit}, then nothing"
    return f"{walked} {unit}, then nothing for {span}"


def _activity_clause(card: dict) -> str:
    """How fast this card is moving. Empty when activity is unknown.

    Unknown is not zero: a failed activity call must not be reported as a
    momentum of 0, so it contributes no clause at all.
    """
    if card.get("momentum") is None:
        return ""
    c7 = card.get("commits_7d") or 0
    c30 = card.get("commits_30d") or 0
    if c7 or c30:
        # Name the sort key and both its inputs: the row shows only c7, which
        # cannot explain why a quieter week outranks a busier one.
        return f"momentum {card['momentum']} - {c7} this week, {c30} this month"
    age = card.get("age")
    span = quiet_span(age, card.get("age_is_floor", False))
    if not span:
        return "no activity recorded"
    # Genuinely zero. "momentum 0 - 0 this week, 0 this month" is honest and
    # unreadable; the quiet wording says the same thing in fewer words.
    if card.get("age_is_floor"):
        return f"no code in {span}"
    return f"quiet for {span}"


def order_reason(card: dict) -> tuple[str, str]:
    """(sentence for the expanded card, badge for the hero)."""
    dtt = card.get("days_to_target")
    clause = _activity_clause(card)

    if dtt is not None and dtt <= URGENT_DAYS:
        if dtt < 0:
            lead, badge = f"{-dtt} days overdue", f"{-dtt}d OVERDUE"
        elif dtt == 0:
            lead, badge = "ships today", "SHIPS today"
        else:
            lead, badge = f"ships in {dtt} days", f"SHIPS {dtt}d"
        # The deadline leads because it is why the card ranks first; the
        # momentum clause gives the pace arrow its numbers.
        return (f"{lead} · {clause}" if clause else lead), badge

    if not clause:
        return "activity unknown", "\u2014"

    c7 = card.get("commits_7d") or 0
    c30 = card.get("commits_30d") or 0
    if c7:
        return clause, f"{c7}/wk"
    if c30:
        return clause, f"{c30}/mo"
    return clause, "quiet"


def why_line(card: dict) -> str:
    """The expanded card's footer: why it ranks here, then what it is owed.

    An overdue card is already named by `order_reason`, so `debt_reason` would
    only state it a second time at the other end of the line. A blocked card is
    not a restatement — the blocker outranks the date in `debt_reason`.
    """
    reason = card.get("order_reason") or ""
    owed = card.get("debt_reason") or ""
    dtt = card.get("days_to_target")
    if owed and not card.get("blocker"):
        overdue_twice = dtt is not None and dtt < 0
        span = quiet_span(card.get("age"), card.get("age_is_floor", False))
        quiet_twice = bool(span) and span in reason
        if overdue_twice or quiet_twice:
            owed = ""
    return " \u00b7 ".join(part for part in (reason, owed) if part)


def commit_cutoffs(now: datetime.datetime) -> tuple[str, str]:
    """(since timestamp for the API, date string for the 7-day boundary)."""
    since = (now - datetime.timedelta(days=MOMENTUM_WINDOW_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    cut7 = (now - datetime.timedelta(days=MOMENTUM_RECENT_DAYS)).date().isoformat()
    return since, cut7


def _commit_day(commit) -> str:
    try:
        return commit["commit"]["committer"]["date"][:10]
    except (KeyError, TypeError, IndexError):
        return ""


def code_commits(payload: list, bookkeeping: list) -> list:
    """Commits that changed something other than STATE.md.

    Maintaining the board must not make a project look worked on. A commit
    that bundles STATE.md with real code is counted as bookkeeping and
    dropped, so an active project undercounts by roughly one commit per
    session while a dormant one collapses to exactly zero.
    """
    skip = {c.get("sha") for c in bookkeeping if isinstance(c, dict) and c.get("sha")}
    return [
        c for c in payload
        if isinstance(c, dict) and c.get("sha") not in skip
    ]


def last_code_day(commits: list) -> str:
    """ISO date of the newest commit given, or "" when there is none."""
    days = [d for d in (_commit_day(c) for c in commits) if d]
    return max(days) if days else ""


def count_commits(payload: list, cut7: str) -> tuple[int, int]:
    """(commits in the recent window, commits in the whole window)."""
    total = len(payload)
    recent = sum(1 for c in payload if _commit_day(c) >= cut7)
    return recent, total
