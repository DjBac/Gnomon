"""Reading STATE.md into typed values. No network, no aiohttp."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import yaml

LOG = logging.getLogger("gnomon")

PHASES = ["idea", "building", "usable", "shipped", "parked"]

# Step prefixes, in the order they appear in a header.
STEP_PREFIXES = {"[x]": "done", "[>]": "current", "[ ]": "todo"}
DEFAULT_STAKES = "personal"
STAKES = ("revenue", "product", "personal")


def parse_front_matter(text: str) -> tuple[dict | None, str]:
    """Extract the leading `---` YAML block. Returns (data, note)."""
    if not text.startswith("---"):
        return None, "STATE.md has no front-matter block"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "STATE.md has no front-matter block"
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as err:
        LOG.warning("Malformed front-matter: %s", err)
        return None, "STATE.md front-matter is not valid YAML"
    if not isinstance(data, dict):
        return None, "STATE.md front-matter is not a mapping"
    return data, ""


def to_date(value) -> date | None:
    """Coerce a YAML date or an ISO string to a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def days_since(value, now: date | None = None) -> int | None:
    """Whole days from `value` until today, UTC."""
    when = to_date(value)
    if when is None:
        return None
    return ((now or today_utc()) - when).days


def days_until(value, now: date | None = None) -> int | None:
    """Whole days from today until `value`, UTC. Negative when overdue."""
    when = to_date(value)
    if when is None:
        return None
    return (when - (now or today_utc())).days


def normalise_phase(value) -> str:
    """A recognised phase, or empty string."""
    phase = str(value or "").strip().lower()
    return phase if phase in PHASES else ""


def normalise_stakes(value) -> str:
    """A recognised stakes level, defaulting to personal."""
    stakes = str(value or "").strip().lower()
    return stakes if stakes in STAKES else DEFAULT_STAKES


def parse_steps(raw) -> tuple[list[dict], str]:
    """Read a `steps` list into typed entries. Returns (steps, note).

    Each entry is `{"text": ..., "state": "done"|"current"|"todo"}`. An
    unrecognised prefix is kept verbatim and treated as todo; only the first
    `[>]` counts as current. A malformed list yields a note, never an
    exception.
    """
    if raw is None:
        return [], ""
    if not isinstance(raw, list):
        return [], "STATE.md steps is not a list"

    steps: list[dict] = []
    skipped = 0
    seen_current = False
    for item in raw:
        if not isinstance(item, str):
            skipped += 1
            continue
        text = item.strip()
        state = "todo"
        for prefix, kind in STEP_PREFIXES.items():
            if text.startswith(prefix):
                state = kind
                text = text[len(prefix):].strip()
                break
        if state == "current":
            if seen_current:
                state = "todo"
            else:
                seen_current = True
        steps.append({"text": text, "state": state})

    note = f"{skipped} step entries were not text" if skipped else ""
    return steps, note


def current_step(steps: list[dict]) -> str:
    for step in steps:
        if step["state"] == "current":
            return step["text"]
    return ""


WATCHED_FIELDS = ("target", "stakes", "phase")


def watched_values(meta: dict) -> dict:
    """The subset of a header worth remembering between polls."""
    target = to_date(meta.get("target"))
    return {
        "target": target.isoformat() if target else "",
        "stakes": str(meta.get("stakes") or "").strip().lower(),
        "phase": normalise_phase(meta.get("phase")),
    }


def vanished(previous: dict, current: dict) -> list[str]:
    """Watched fields that had a value last time and have none now."""
    if not previous:
        return []
    return [f for f in WATCHED_FIELDS if previous.get(f) and not current.get(f)]


def vanished_note(gone: list[str]) -> str:
    if not gone:
        return ""
    return f"{', '.join(gone)} removed since last poll"
