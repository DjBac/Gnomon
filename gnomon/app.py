"""Gnomon — at-a-glance project status board for Home Assistant.

Polls a list of GitHub repositories, reads the YAML front-matter block from
each repo's STATE.md, and serves a single-page panel over HA ingress.

Facts come from the GitHub API. Judgments come from STATE.md. Freshness is
derived from the repo's last push, never from a hand-maintained date, and
ordering is computed from deadline, momentum and stakes rather than stored.

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
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from aiohttp import web

import github
import ranking
import state

LOG = logging.getLogger("gnomon")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

OPTIONS_PATH = Path("/data/options.json")
WWW_DIR = Path(__file__).parent / "www"
PORT = 8099


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


def new_card(repo: str) -> dict:
    return {
        "repo": repo,
        "project": repo.split("/")[-1],
        "phase": "",
        "stakes": state.DEFAULT_STAKES,
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
        "commits_7d": None,
        "commits_30d": None,
        "momentum": None,
        "debt": 0.0,
        "debt_reason": "",
        "role": "tail",
        "order_reason": "",
        "order_badge": "",
        "note": "",
    }


SEEN_PATH = Path("/data/gnomon-seen.json")


def load_seen() -> dict:
    """Last-seen watched fields per repo. Absent or corrupt reads as empty."""
    try:
        with SEEN_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_seen(seen: dict) -> None:
    try:
        SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SEEN_PATH.open("w", encoding="utf-8") as handle:
            json.dump(seen, handle)
    except OSError as err:
        LOG.warning("Could not persist seen-state: %s", err)


async def fetch_repo(
    session: aiohttp.ClientSession,
    repo: str,
    stale_days: int,
    since: str,
    cut7: str,
    seen: dict,
) -> dict:
    """Build one card from repo metadata, STATE.md and commit activity."""
    card = new_card(repo)

    pushed_at, note = await github.fetch_pushed_at(session, repo)
    if pushed_at:
        card["updated"] = str(pushed_at)[:10]
        card["age"] = state.days_since(pushed_at)
    if note:
        # A metadata failure means we have no facts at all — say so and stop.
        card["note"] = note
        card["state"] = ranking.classify("", "", card["age"], stale_days)
        return card

    payload, activity_note = await github.fetch_commits(session, repo, since)
    if payload is not None:
        card["commits_7d"], card["commits_30d"] = ranking.count_commits(payload, cut7)
        card["momentum"] = ranking.momentum(card["commits_7d"], card["commits_30d"])

    body, state_note = await github.fetch_state_md(session, repo)
    meta: dict = {}
    if body is None:
        card["note"] = state_note
    else:
        parsed, parse_note = state.parse_front_matter(body)
        if parsed is None:
            card["note"] = parse_note
        else:
            meta = parsed

    card["project"] = str(meta.get("project") or card["project"]).strip()
    card["phase"] = state.normalise_phase(meta.get("phase"))
    card["stakes"] = state.normalise_stakes(meta.get("stakes"))
    card["blocker"] = str(meta.get("blocker") or "").strip()

    steps, steps_note = state.parse_steps(meta.get("steps"))
    card["steps"] = steps
    card["steps_total"] = len(steps)
    card["steps_done"] = sum(1 for s in steps if s["state"] == "done")
    # `next` is derived from the current step; a legacy header without
    # `steps` still renders from its own `next` field.
    card["next"] = state.current_step(steps) or (
        "" if steps else str(meta.get("next") or "").strip()
    )

    target = state.to_date(meta.get("target"))
    if target is not None:
        card["target"] = target.isoformat()
        card["days_to_target"] = state.days_until(target)

    card["state"] = ranking.classify(
        card["blocker"], card["phase"], card["age"], stale_days
    )
    card["debt"] = ranking.debt(
        card["age"], stale_days, card["blocker"], card["days_to_target"]
    )
    card["debt_reason"] = ranking.debt_reason(
        card["age"], stale_days, card["blocker"], card["days_to_target"]
    )
    card["order_reason"], card["order_badge"] = ranking.order_reason(card)

    current = state.watched_values(meta)
    gone = state.vanished(seen.get(repo, {}), current)
    seen[repo] = current

    for candidate in (activity_note, steps_note, state.vanished_note(gone)):
        if candidate and not card["note"]:
            card["note"] = candidate
    if not card["note"] and not card["next"]:
        card["note"] = "No next action set"
    return card


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
            "phases": state.PHASES,
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

    since, cut7 = ranking.commit_cutoffs(datetime.now(timezone.utc))
    seen = load_seen()
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        cards = await asyncio.gather(
            *(
                fetch_repo(session, repo, stale_days, since, cut7, seen)
                for repo in repos
            )
        )
    save_seen(seen)

    ordered = sorted(list(cards), key=ranking.order_key)
    ranking.assign_roles(ordered)
    app["cache"] = {
        "projects": ordered,
        "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stale_days": stale_days,
        "phases": state.PHASES,
        "error": None,
    }
    LOG.info("Refreshed %d repos", len(ordered))


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


def main() -> None:
    app = web.Application()
    app["options"] = load_options()
    app["cache"] = {
        "projects": [],
        "fetched": None,
        "stale_days": int(app["options"].get("stale_days", 14)),
        "phases": state.PHASES,
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
    main()
