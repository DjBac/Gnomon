"""GitHub API calls. The only module that touches the network."""

from __future__ import annotations

import asyncio
import json

import aiohttp

GITHUB_API = "https://api.github.com"


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
