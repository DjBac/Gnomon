"""Dependency-free tests. Run: python3 gnomon/selftest.py"""

from __future__ import annotations

import pathlib
import sys

import ranking
import state


def selftest_no_network_deps() -> int:
    """state and ranking must stay importable without aiohttp."""
    here = pathlib.Path(__file__).parent
    bad = []
    for name in ("state", "ranking"):
        source = (here / f"{name}.py").read_text(encoding="utf-8")
        if "import aiohttp" in source or "from aiohttp" in source:
            bad.append(name)
    print(f"{'FAIL' if bad else 'PASS'}  pure modules free of aiohttp"
          f"{': ' + ', '.join(bad) if bad else ''}")
    return 1 if bad else 0


def selftest_priority() -> int:
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
        got_score = ranking.compute_score(stakes, dtt, blocker, phase)
        got_band = ranking.band(got_score)
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
        parts = ranking.score_factors(stakes, dtt, blocker, phase)
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
        steps, note = state.parse_steps(meta.get("steps"))
        total = len(steps)
        done = sum(1 for s in steps if s["state"] == "done")
        nxt = state.current_step(steps) or ("" if steps else str(meta.get("next") or "").strip())
        ok = total == want_total and done == want_done and nxt == want_next
        failures += not ok
        print(
            f"{'PASS' if ok else 'FAIL'}  {label:22} total={total} done={done} "
            f"next={nxt!r}{'  note=' + note if note else ''}"
            f"{'' if ok else f'  (want {want_total}/{want_done}/{want_next!r})'}"
        )
    # states of the unprefixed case, spelled out
    steps, _ = state.parse_steps(["no prefix here", "[x] done", "[>] now"])
    print(f"\nprefix handling: {[(s['text'], s['state']) for s in steps]}")
    print(f"{len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


def main() -> int:
    failures = 0
    failures += selftest_no_network_deps()
    failures += selftest_priority()
    failures += selftest_steps()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
