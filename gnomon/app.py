"""Gnomon — at-a-glance project status board for Home Assistant.

Polls a list of GitHub repositories, reads the YAML front-matter block from
each repo's STATE.md, and serves a single-page panel over HA ingress.

Facts come from the GitHub API. Judgments come from STATE.md. Freshness is
derived from the repo's last push, never from a hand-maintained date, and
priority is computed from stakes, target and blocker rather than stored.

Expected STATE.md header:

    ---
    project: Nostos
    phase: building
    stakes: revenue
    target: 2027-09-30
    blocker: ""
    steps:
      - "[x] Branded delivery pages"
      - "[>] Wire Stripe webhook to delivery unlock"
      - "[ ] Timeline review UI"
    ---
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import aiohttp
import yaml
from aiohttp import web

LOG = logging.getLogger("gnomon")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

OPTIONS_PATH = Path("/data/options.json")
WWW_DIR = Path(__file__).parent / "www"
GITHUB_API = "https://api.github.com"
PORT = 8099

# Freshness bands, in days since the repo's last push.
FRESH_MAX = 6

PHASES = ["idea", "building", "usable", "shipped", "parked"]

# Step prefixes, in the order they appear in a header.
STEP_PREFIXES = {"[x]": "done", "[>]": "current", "[ ]": "todo"}
STAKES_BASE = {"revenue": 4.0, "product": 2.0, "personal": 1.0}
DEFAULT_STAKES = "personal"

BLOCKED_MULTIPLIER = 1.4
PARKED_MULTIPLIER = 0.2


def load_options() -> dict:
    """Read add-on options, falling back to env vars for local dev.

    Called on every poll cycle so a config change takes effect without a
    restart.
    """
    if OPTIONS_PATH.exists():
        try:
            with OPTIONS_PATH.open(encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as err:
            LOG.warning("Could not read options: %s", err)
            return {}
    return {
        "github_token": os.environ.get("GITHUB_TOKEN", ""),
        "repos": [r for r in os.environ.get("REPOS", "").split(",") if r],
        "poll_minutes": int(os.environ.get("POLL_MINUTES", "15")),
        "stale_days": int(os.environ.get("STALE_DAYS", "14")),
    }


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
    return stakes if stakes in STAKES_BASE else DEFAULT_STAKES


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


def new_card(repo: str) -> dict:
    return {
        "repo": repo,
        "project": repo.split("/")[-1],
        "phase": "",
        "stakes": DEFAULT_STAKES,
        "target": "",
        "days_to_target": None,
        "next": "",
        "steps": [],
        "steps_done": 0,
        "steps_total": 0,
        "blocker": "",
        "updated": None,
        "age": None,
        "state": "unknown",
        "priority": "low",
        "score": 0.0,
        "score_factors": [],
        "note": "",
    }


def meta_note(status: int) -> str:
    if status == 401:
        return "Token rejected — check scopes"
    if status == 403:
        return "Forbidden — token lacks access"
    if status == 404:
        return "Repo not found — check name and casing"
    return f"GitHub returned {status}"


async def fetch_pushed_at(session: aiohttp.ClientSession, repo: str) -> tuple[str | None, str]:
    """Repo metadata call. Returns (pushed_at, note)."""
    url = f"{GITHUB_API}/repos/{repo}"
    try:
        async with session.get(url, headers={"Accept": "application/vnd.github+json"}) as response:
            if response.status != 200:
                return None, meta_note(response.status)
            data = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        return None, f"Fetch failed: {type(err).__name__}"
    except (json.JSONDecodeError, ValueError):
        return None, "GitHub returned an unreadable response"
    if not isinstance(data, dict):
        return None, "GitHub returned an unreadable response"
    return data.get("pushed_at"), ""


async def fetch_state_md(session: aiohttp.ClientSession, repo: str) -> tuple[str | None, str]:
    """STATE.md contents call. Returns (body, note)."""
    url = f"{GITHUB_API}/repos/{repo}/contents/STATE.md"
    try:
        async with session.get(
            url, headers={"Accept": "application/vnd.github.raw+json"}
        ) as response:
            if response.status == 404:
                return None, "No STATE.md in this repo"
            if response.status != 200:
                return None, meta_note(response.status)
            return await response.text(), ""
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        return None, f"Fetch failed: {type(err).__name__}"


async def fetch_repo(session: aiohttp.ClientSession, repo: str, stale_days: int) -> dict:
    """Build one card from repo metadata plus STATE.md."""
    card = new_card(repo)

    pushed_at, note = await fetch_pushed_at(session, repo)
    if pushed_at:
        card["updated"] = str(pushed_at)[:10]
        card["age"] = days_since(pushed_at)
    if note:
        # A metadata failure means we have no facts at all — say so and stop.
        card["note"] = note
        card["state"] = classify("", "", card["age"], stale_days)
        card["score"] = compute_score(card["stakes"], None, "", "")
        card["score_factors"] = score_factors(card["stakes"], None, "", "")
        card["priority"] = band(card["score"])
        return card

    body, state_note = await fetch_state_md(session, repo)
    meta: dict = {}
    if body is None:
        card["note"] = state_note
    else:
        parsed, parse_note = parse_front_matter(body)
        if parsed is None:
            card["note"] = parse_note
        else:
            meta = parsed

    card["project"] = str(meta.get("project") or card["project"]).strip()
    card["phase"] = normalise_phase(meta.get("phase"))
    card["stakes"] = normalise_stakes(meta.get("stakes"))
    card["blocker"] = str(meta.get("blocker") or "").strip()

    steps, steps_note = parse_steps(meta.get("steps"))
    card["steps"] = steps
    card["steps_total"] = len(steps)
    card["steps_done"] = sum(1 for s in steps if s["state"] == "done")
    # `next` is derived from the current step; a legacy header without
    # `steps` still renders from its own `next` field.
    card["next"] = current_step(steps) or (
        "" if steps else str(meta.get("next") or "").strip()
    )
    if steps_note and not card["note"]:
        card["note"] = steps_note

    target = to_date(meta.get("target"))
    if target is not None:
        card["target"] = target.isoformat()
        card["days_to_target"] = days_until(target)

    card["state"] = classify(card["blocker"], card["phase"], card["age"], stale_days)
    card["score"] = compute_score(
        card["stakes"], card["days_to_target"], card["blocker"], card["phase"]
    )
    card["score_factors"] = score_factors(
        card["stakes"], card["days_to_target"], card["blocker"], card["phase"]
    )
    card["priority"] = band(card["score"])

    if not card["note"] and not card["next"]:
        card["note"] = "No next action set"
    return card


def sort_cards(cards: list[dict]) -> list[dict]:
    """Descending by score, then descending by age."""
    return sorted(
        cards,
        key=lambda c: (
            -c["score"],
            -(c["age"] if c["age"] is not None else -1),
        ),
    )


async def refresh(app: web.Application) -> None:
    """Pull every configured repo and cache the result."""
    options = load_options()
    app["options"] = options

    stale_days = int(options.get("stale_days", 14))
    repos = options.get("repos") or []
    if not repos:
        app["cache"] = {
            "projects": [],
            "fetched": None,
            "stale_days": stale_days,
            "phases": PHASES,
            "error": "No repos configured",
        }
        return

    headers = {
        "User-Agent": "gnomon",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = options.get("github_token") or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        cards = await asyncio.gather(
            *(fetch_repo(session, repo, stale_days) for repo in repos)
        )

    app["cache"] = {
        "projects": sort_cards(list(cards)),
        "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stale_days": stale_days,
        "phases": PHASES,
        "error": None,
    }
    LOG.info("Refreshed %d repos", len(cards))


async def poll_loop(app: web.Application) -> None:
    while True:
        try:
            await refresh(app)
        except Exception:  # noqa: BLE001 — a poll failure must not kill the loop
            LOG.exception("Refresh cycle failed")
        interval = max(1, int(app["options"].get("poll_minutes", 15))) * 60
        await asyncio.sleep(interval)


async def handle_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(WWW_DIR / "index.html")


async def handle_projects(request: web.Request) -> web.Response:
    return web.json_response(request.app["cache"])


async def handle_refresh(request: web.Request) -> web.Response:
    await refresh(request.app)
    return web.json_response(request.app["cache"])


async def on_startup(app: web.Application) -> None:
    app["poller"] = asyncio.create_task(poll_loop(app))


async def on_cleanup(app: web.Application) -> None:
    app["poller"].cancel()


def selftest() -> int:
    """Acceptance tests for the computed-priority formula."""
    cases = [
        ("revenue", 420, "", "building", 4.0, "high"),
        ("revenue", 20, "", "building", 9.6, "high"),
        ("revenue", -5, "", "shipped", 12.0, "high"),
        ("product", None, "", "shipped", 2.0, "normal"),
        ("product", None, "", "parked", 0.4, "low"),
        ("personal", None, "", "usable", 1.0, "low"),
        ("personal", None, "waiting on vendor", "shipped", 1.4, "low"),
    ]
    failures = 0
    for stakes, dtt, blocker, phase, want_score, want_band in cases:
        got_score = compute_score(stakes, dtt, blocker, phase)
        got_band = band(got_score)
        ok = got_score == want_score and got_band == want_band
        failures += not ok
        target = "no target" if dtt is None else f"target {dtt:+d}d"
        blocked = "blocked" if blocker else "not blocked"
        print(
            f"{'PASS' if ok else 'FAIL'}  {stakes:8} {target:14} {blocked:11} "
            f"{phase:8} -> {got_score:5} {got_band:6}"
            f"{'' if ok else f'  (want {want_score} {want_band})'}"
        )
    # the displayed reasoning must multiply back to the sorted number
    recon = 0
    for stakes, dtt, blocker, phase, want_score, _ in cases:
        parts = score_factors(stakes, dtt, blocker, phase)
        product = 1.0
        for p in parts:
            product *= p["factor"]
        if round(product, 2) != want_score:
            recon += 1
            print(f"FAIL  factors do not reconcile: {parts} -> {product}")
    print(f"factors reconcile with score: {'yes' if not recon else 'NO'}")

    print(f"\n{len(cases) - failures - recon}/{len(cases)} passed")
    return 1 if (failures or recon) else 0


def selftest_steps() -> int:
    """Acceptance tests for the step parser."""
    seven = [
        "[x] Proposal page, static and data-driven",
        "[x] View tracking and holds",
        "[x] Admin dashboard with Blob upload",
        "[x] Venue management and treatment drafting",
        "[x] Domain redirects and the Phase 7 gate",
        "[>] Drafting quality for venues nobody has visited",
        "[ ] Ship the proposal system",
    ]
    cases = [
        ("normal 7-step list", {"steps": seven}, 7, 5, "Drafting quality for venues nobody has visited"),
        ("empty list", {"steps": []}, 0, 0, ""),
        ("missing key", {"project": "X"}, 0, 0, ""),
        ("two current markers", {"steps": ["[>] first", "[>] second", "[x] done"]}, 3, 1, "first"),
        ("unprefixed string", {"steps": ["no prefix here", "[x] done"]}, 2, 1, ""),
        ("legacy next, no steps", {"next": "Wire the webhook"}, 0, 0, "Wire the webhook"),
        ("steps not a list", {"steps": "oops"}, 0, 0, ""),
        ("non-string entries", {"steps": ["[x] real", 42, None]}, 1, 1, ""),
    ]
    failures = 0
    for label, meta, want_total, want_done, want_next in cases:
        steps, note = parse_steps(meta.get("steps"))
        total = len(steps)
        done = sum(1 for s in steps if s["state"] == "done")
        nxt = current_step(steps) or ("" if steps else str(meta.get("next") or "").strip())
        ok = total == want_total and done == want_done and nxt == want_next
        failures += not ok
        print(
            f"{'PASS' if ok else 'FAIL'}  {label:22} total={total} done={done} "
            f"next={nxt!r}{'  note=' + note if note else ''}"
            f"{'' if ok else f'  (want {want_total}/{want_done}/{want_next!r})'}"
        )
    # states of the unprefixed case, spelled out
    steps, _ = parse_steps(["no prefix here", "[x] done", "[>] now"])
    print(f"\nprefix handling: {[(s['text'], s['state']) for s in steps]}")
    print(f"{len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


def main() -> None:
    app = web.Application()
    app["options"] = load_options()
    app["cache"] = {
        "projects": [],
        "fetched": None,
        "stale_days": int(app["options"].get("stale_days", 14)),
        "phases": PHASES,
        "error": "Loading...",
    }

    app.router.add_get("/", handle_index)
    app.router.add_get("/api/projects", handle_projects)
    app.router.add_post("/api/refresh", handle_refresh)
    app.router.add_static("/static", WWW_DIR)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    LOG.info("Listening on :%d", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT, access_log=None)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest() or selftest_steps())
    main()
