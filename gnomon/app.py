"""Gnomon — at-a-glance project status board for Home Assistant.

Polls a list of GitHub repositories, reads the YAML front-matter block from
each repo's STATE.md, and serves a single-page panel over HA ingress.

Expected STATE.md header:

    ---
    project: Nostos
    next: "Wire Stripe webhook to delivery unlock"
    blocker: ""
    updated: 2026-08-06
    ---
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
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

# Freshness bands, in days since `updated`.
FRESH_MAX = 6


def load_options() -> dict:
    """Read add-on options, falling back to env vars for local dev."""
    if OPTIONS_PATH.exists():
        with OPTIONS_PATH.open(encoding="utf-8") as handle:
            return json.load(handle)
    return {
        "github_token": os.environ.get("GITHUB_TOKEN", ""),
        "repos": [r for r in os.environ.get("REPOS", "").split(",") if r],
        "poll_minutes": int(os.environ.get("POLL_MINUTES", "15")),
        "stale_days": int(os.environ.get("STALE_DAYS", "14")),
    }


def parse_front_matter(text: str) -> dict | None:
    """Extract and parse the leading `---` YAML block from a markdown file."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as err:
        LOG.warning("Malformed front-matter: %s", err)
        return None
    return data if isinstance(data, dict) else None


def days_since(value) -> int | None:
    """Days between `updated` and today. Accepts a date or an ISO string."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    if not isinstance(value, date):
        return None
    return (datetime.now(timezone.utc).date() - value).days


def classify(blocker: str, age: int | None, stale_days: int) -> str:
    if blocker:
        return "blocked"
    if age is None:
        return "unknown"
    if age <= FRESH_MAX:
        return "fresh"
    if age <= stale_days:
        return "aging"
    return "stale"


async def fetch_repo(session: aiohttp.ClientSession, repo: str, stale_days: int) -> dict:
    """Fetch and interpret one repo's STATE.md."""
    card = {
        "repo": repo,
        "project": repo.split("/")[-1],
        "next": "",
        "blocker": "",
        "updated": None,
        "age": None,
        "state": "unknown",
        "note": "",
    }

    url = f"{GITHUB_API}/repos/{repo}/contents/STATE.md"
    try:
        async with session.get(url) as response:
            if response.status == 404:
                card["note"] = "No STATE.md in this repo"
                return card
            if response.status == 401:
                card["note"] = "Token rejected — check scopes"
                return card
            if response.status != 200:
                card["note"] = f"GitHub returned {response.status}"
                return card
            body = await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        card["note"] = f"Fetch failed: {type(err).__name__}"
        return card

    meta = parse_front_matter(body)
    if meta is None:
        card["note"] = "STATE.md has no front-matter block"
        return card

    card["project"] = str(meta.get("project") or card["project"])
    card["next"] = str(meta.get("next") or "").strip()
    card["blocker"] = str(meta.get("blocker") or "").strip()

    raw_updated = meta.get("updated")
    card["age"] = days_since(raw_updated)
    if isinstance(raw_updated, (date, datetime)):
        card["updated"] = raw_updated.isoformat()[:10]
    elif raw_updated:
        card["updated"] = str(raw_updated)[:10]

    card["state"] = classify(card["blocker"], card["age"], stale_days)
    if not card["next"]:
        card["note"] = "No next action set"
    return card


ORDER = {"blocked": 0, "stale": 1, "unknown": 2, "aging": 3, "fresh": 4}


async def refresh(app: web.Application) -> None:
    """Pull every configured repo and cache the result."""
    options = app["options"]
    repos = options.get("repos") or []
    if not repos:
        app["cache"] = {"projects": [], "fetched": None, "error": "No repos configured"}
        return

    headers = {
        "Accept": "application/vnd.github.raw+json",
        "User-Agent": "gnomon",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = options.get("github_token") or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"

    timeout = aiohttp.ClientTimeout(total=20)
    stale_days = int(options.get("stale_days", 14))

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        cards = await asyncio.gather(
            *(fetch_repo(session, repo, stale_days) for repo in repos)
        )

    cards = sorted(
        cards,
        key=lambda c: (ORDER.get(c["state"], 9), -(c["age"] if c["age"] is not None else 0)),
    )
    app["cache"] = {
        "projects": cards,
        "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stale_days": stale_days,
        "error": None,
    }
    LOG.info("Refreshed %d repos", len(cards))


async def poll_loop(app: web.Application) -> None:
    interval = max(1, int(app["options"].get("poll_minutes", 15))) * 60
    while True:
        try:
            await refresh(app)
        except Exception:  # noqa: BLE001 — a poll failure must not kill the loop
            LOG.exception("Refresh cycle failed")
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
    app["cache"] = {"projects": [], "fetched": None, "error": "Loading..."}

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
