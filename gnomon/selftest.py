"""Dependency-free tests. Run: python3 gnomon/selftest.py"""

from __future__ import annotations

import datetime
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


def selftest_commits() -> int:
    """Counting commits out of an API payload."""
    def c(day):
        return {"commit": {"committer": {"date": f"{day}T10:00:00Z"}}}

    cases = [
        ("all recent", [c("2026-08-20"), c("2026-08-19")], "2026-08-14", (2, 2)),
        ("split window", [c("2026-08-20"), c("2026-08-01")], "2026-08-14", (1, 2)),
        ("none recent", [c("2026-08-01"), c("2026-07-25")], "2026-08-14", (0, 2)),
        ("empty", [], "2026-08-14", (0, 0)),
        ("malformed entry", [c("2026-08-20"), {"nope": 1}], "2026-08-14", (1, 2)),
        ("boundary is inclusive", [c("2026-08-14")], "2026-08-14", (1, 1)),
    ]
    failures = 0
    for label, payload, cut7, want in cases:
        got = ranking.count_commits(payload, cut7)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  commits: {label:24} {got}"
              f"{'' if ok else f'  (want {want})'}")

    since, cut7 = ranking.commit_cutoffs(
        datetime.datetime(2026, 8, 21, 12, 0, tzinfo=datetime.timezone.utc)
    )
    ok = since.startswith("2026-07-22") and cut7 == "2026-08-14"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  commits: cutoffs               {since} / {cut7}")
    return 1 if failures else 0


def selftest_momentum() -> int:
    cases = [
        ("very active", 51, 51, 204),
        ("steady", 17, 100, 151),
        ("quiet", 0, 0, 0),
        ("old work only", 0, 12, 12),
        ("unknown stays unknown", None, None, None),
    ]
    failures = 0
    for label, c7, c30, want in cases:
        got = ranking.momentum(c7, c30)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  momentum: {label:22} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0


def selftest_debt() -> int:
    cases = [
        ("fresh and fine", 2, 14, "", None, 0.14),
        ("one stale period", 14, 14, "", None, 1.0),
        ("blocked", 0, 14, "vendor key", None, 1.5),
        ("overdue", 0, 14, "", -3, 2.0),
        ("everything at once", 28, 14, "vendor key", -3, 5.5),
        ("no age", None, 14, "", None, 0.0),
    ]
    failures = 0
    for label, age, sd, blk, dtt, want in cases:
        got = ranking.debt(age, sd, blk, dtt)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  debt: {label:26} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0


def _card(repo, **kw):
    base = dict(repo=repo, project=repo, stakes="personal", phase="usable",
                blocker="", next="do a thing", age=3, days_to_target=None,
                momentum=0, commits_7d=0, commits_30d=0, debt=0.0, role="tail")
    base.update(kw)
    return base


def selftest_ordering() -> int:
    failures = 0

    # a near deadline outranks higher momentum
    cards = [_card("busy", momentum=200), _card("due", days_to_target=12, momentum=1)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["due", "busy"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: deadline beats momentum  {got}")

    # a distant target does not enter the urgent tier
    cards = [_card("busy", momentum=200), _card("far", days_to_target=400, momentum=1)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["busy", "far"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: distant target waits     {got}")

    # two deadlines sort soonest first
    cards = [_card("later", days_to_target=20), _card("sooner", days_to_target=3)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["sooner", "later"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: soonest deadline first   {got}")

    # momentum orders the rest, unknown sorts as quiet
    cards = [_card("mid", momentum=50), _card("top", momentum=99),
             _card("unknown", momentum=None), _card("low", momentum=1)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["top", "mid", "low", "unknown"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: momentum descending      {got}")

    # stakes breaks a momentum tie
    cards = [_card("personal-one", momentum=5),
             _card("revenue-one", momentum=5, stakes="revenue")]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["revenue-one", "personal-one"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: stakes breaks the tie    {got}")
    return 1 if failures else 0


def selftest_roles() -> int:
    failures = 0

    def roles(cards):
        ordered = sorted(cards, key=ranking.order_key)
        ranking.assign_roles(ordered)
        return {c["repo"]: c["role"] for c in ordered}

    # hero is the top card
    got = roles([_card("a", momentum=10), _card("b", momentum=1)])
    ok = got["a"] == "hero" and got["b"] == "tail"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: top card is hero         {got}")

    # hero suppressed only when all three are true
    got = roles([_card("empty", momentum=0, next="", days_to_target=None)])
    ok = got["empty"] == "tail"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: quiet board has no hero  {got}")

    # unknown momentum must not suppress the hero
    got = roles([_card("unknown", momentum=None, next="", days_to_target=None)])
    ok = got["unknown"] == "hero"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: unknown keeps the hero   {got}")

    # rescue must come from rank 5 or lower
    pool = [_card(f"r{i}", momentum=100 - i, debt=0.0) for i in range(4)]
    pool.append(_card("rotting", momentum=1, debt=3.0))
    got = roles(pool)
    ok = got["rotting"] == "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: rescue from below fold   {got.get('rotting')}")

    # a high-debt card already visible is NOT rescued
    pool = [_card("visible", momentum=100, debt=9.0)] + \
           [_card(f"r{i}", momentum=50 - i) for i in range(5)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: visible debt not rescued {sorted(set(got.values()))}")

    # below the floor, no rescue slot at all
    pool = [_card(f"r{i}", momentum=50 - i, debt=0.5) for i in range(8)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: floor respected          {sorted(set(got.values()))}")

    # parked is never rescued
    pool = [_card(f"r{i}", momentum=50 - i) for i in range(5)]
    pool.append(_card("parked", momentum=0, debt=9.0, phase="parked"))
    got = roles(pool)
    ok = got["parked"] != "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: parked never rescued     {got['parked']}")
    return 1 if failures else 0


def selftest_order_reason() -> int:
    cases = [
        ("ships soon", _card("a", days_to_target=12),
         ("ships in 12 days", "SHIPS 12d")),
        ("ships today", _card("a", days_to_target=0),
         ("ships today", "SHIPS today")),
        ("overdue", _card("a", days_to_target=-3),
         ("3 days overdue", "3d OVERDUE")),
        ("active", _card("a", commits_7d=51, commits_30d=51, momentum=204),
         ("51 commits this week", "51/wk")),
        ("one commit", _card("a", commits_7d=1, commits_30d=1, momentum=4),
         ("1 commit this week", "1/wk")),
        ("older work only", _card("a", commits_7d=0, commits_30d=9, momentum=9),
         ("9 commits this month", "9/mo")),
        ("quiet", _card("a", commits_7d=0, commits_30d=0, momentum=0, age=94),
         ("quiet for 94 days", "quiet")),
        ("unknown", _card("a", momentum=None, commits_7d=None, commits_30d=None),
         ("activity unknown", "—")),
    ]
    failures = 0
    for label, card, want in cases:
        got = ranking.order_reason(card)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  reason: {label:20} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0


GOLDEN = [
    # repo,                              stakes,     phase,     dtt,  c7, c30, blocker, age
    ("DjBac/anthonyvenitis",              "revenue",  "usable",   12,   2,  25, "",        4),
    ("DjBac/argus",                       "personal", "usable", None,  51,  51, "",        0),
    ("DjBac/premiere",                    "revenue",  "usable", None,  17, 100, "walk",    4),
    ("DjBac/nima",                        "product",  "building", None, 29, 52, "",        4),
    ("DjBac/the-bridge",                  "product",  "building", None, 22, 22, "queue",   1),
    ("DjBac/oikovis-automations",         "personal", "usable", None,   2,  15, "",        4),
    ("DjBac/Gnomon",                      "personal", "usable", None,   4,   7, "",        0),
    ("DjBac/pounta-sunbed-booking",       "personal", "usable", None,   1,   8, "",        4),
    ("DjBac/pilates-autobooker",          "personal", "usable", None,   1,   1, "",        4),
    ("DjBac/ha-doukas-bus",               "personal", "shipped", None,  1,   1, "",        4),
    ("Oikovis/pulse",                     "product",  "building", None, 1,   1, "",        4),
]


def selftest_golden_order() -> int:
    """The eleven real headers must produce the approved order."""
    cards = []
    for repo, stakes, phase, dtt, c7, c30, blocker, age in GOLDEN:
        card = _card(repo, stakes=stakes, phase=phase, days_to_target=dtt,
                     commits_7d=c7, commits_30d=c30, blocker=blocker, age=age)
        card["momentum"] = ranking.momentum(c7, c30)
        card["debt"] = ranking.debt(age, 14, blocker, dtt)
        cards.append(card)
    ordered = sorted(cards, key=ranking.order_key)
    ranking.assign_roles(ordered)
    got = [c["repo"] for c in ordered]
    want = ["DjBac/anthonyvenitis", "DjBac/argus", "DjBac/premiere",
            "DjBac/nima", "DjBac/the-bridge", "DjBac/oikovis-automations",
            "DjBac/Gnomon", "DjBac/pounta-sunbed-booking", "Oikovis/pulse",
            "DjBac/ha-doukas-bus", "DjBac/pilates-autobooker"]
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  golden order")
    if not ok:
        print(f"    got  {got}")
        print(f"    want {want}")
    hero = [c["repo"] for c in ordered if c["role"] == "hero"]
    hero_ok = hero == ["DjBac/anthonyvenitis"]
    print(f"{'PASS' if hero_ok else 'FAIL'}  golden hero: {hero}")
    # premiere carries a blocker but sits at rank 3, so it is NOT rescued;
    # the-bridge is the highest-debt card at rank 5 or lower.
    rescue = [c["repo"] for c in ordered if c["role"] == "rescue"]
    rescue_ok = rescue == ["DjBac/the-bridge"]
    print(f"{'PASS' if rescue_ok else 'FAIL'}  golden rescue: {rescue}")
    return 0 if (ok and hero_ok and rescue_ok) else 1


def selftest_debt_never_orders() -> int:
    """Debt marks a card for rescue; it must never move it, at any tiebreak point.

    All four cards tie on tier, momentum, and stakes, so with debt playing no
    part the only remaining tiebreak is repo name. If any refactor smuggles
    debt into order_key anywhere before that last field -- as a dominant
    term or a subtle tiebreak -- some permutation below will reorder the
    cards and expose it.
    """
    failures = 0
    repos = ["alpha", "beta", "gamma", "delta"]
    want = ["alpha", "beta", "delta", "gamma"]  # alphabetical, the only live tiebreak

    debt_assignments = [
        [0.0, 0.0, 0.0, 0.0],
        [9.0, 0.0, 0.0, 0.0],
        [0.0, 9.0, 0.0, 0.0],
        [0.0, 0.0, 9.0, 0.0],
        [0.0, 0.0, 0.0, 9.0],
        [5.0, 1.0, 9.0, 0.0],
        [0.0, 9.0, 5.0, 1.0],
    ]
    for debts in debt_assignments:
        cards = [
            _card(repo, stakes="personal", momentum=7, debt=d)
            for repo, d in zip(repos, debts)
        ]
        got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  order: debt never a tiebreak {debts} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0


def selftest_rescue_selection() -> int:
    """With several debt-eligible cards below the fold, rescue picks exactly
    one -- the highest-debt candidate -- never zero, never more than one,
    and never the wrong one."""
    failures = 0
    pool = [_card(f"r{i}", momentum=100 - i) for i in range(4)]  # ranks 1-4, ineligible
    pool += [
        _card("low-debt", momentum=10, debt=2.0),
        _card("high-debt", momentum=9, debt=5.0),
        _card("mid-debt", momentum=8, debt=3.0),
    ]
    ordered = sorted(pool, key=ranking.order_key)
    ranking.assign_roles(ordered)
    rescues = [c["repo"] for c in ordered if c["role"] == "rescue"]

    ok_count = len(rescues) == 1
    failures += not ok_count
    print(f"{'PASS' if ok_count else 'FAIL'}  rescue: exactly one candidate   {rescues}")

    ok_pick = rescues == ["high-debt"]
    failures += not ok_pick
    print(f"{'PASS' if ok_pick else 'FAIL'}  rescue: picks highest debt      {rescues}")
    return 1 if failures else 0


def selftest_debt_reason() -> int:
    cases = [
        ("blocked wins over overdue", 0, 14, "vendor key", -3, "blocked"),
        ("overdue wins over age", 0, 14, "", -3, "3d overdue"),
        ("age when neither", 20, 14, "", None, "quiet 20 days"),
        ("empty when age is None", None, 14, "", None, ""),
    ]
    failures = 0
    for label, age, sd, blk, dtt, want in cases:
        got = ranking.debt_reason(age, sd, blk, dtt)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  debt_reason: {label:26} {got!r}"
              f"{'' if ok else f'  (want {want!r})'}")
    return 1 if failures else 0


def selftest_watched_values() -> int:
    """Watched values normalisation for change detection."""
    cases = [
        ("YAML date object",
         {"target": datetime.date(2027, 9, 30), "stakes": "revenue", "phase": "usable"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}),
        ("ISO string date",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}),
        ("mixed-case stakes",
         {"target": "2027-09-30", "stakes": "Revenue", "phase": "usable"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}),
        ("mixed-case phase",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "BUILDING"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "building"}),
        ("unrecognised phase",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "bogus"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": ""}),
        ("missing fields",
         {},
         {"target": "", "stakes": "", "phase": ""}),
        ("empty target",
         {"target": "", "stakes": "revenue", "phase": "usable"},
         {"target": "", "stakes": "revenue", "phase": "usable"}),
    ]
    failures = 0
    for label, meta, want in cases:
        got = state.watched_values(meta)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  watched_values: {label:24} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0


def selftest_vanished() -> int:
    cases = [
        ("nothing changed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}, []),
        ("target removed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "", "stakes": "revenue", "phase": "usable"}, ["target"]),
        ("target changed, not removed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "2028-01-01", "stakes": "revenue", "phase": "usable"}, []),
        ("two removed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "", "stakes": "revenue", "phase": ""}, ["target", "phase"]),
        ("never had one",
         {"target": "", "stakes": "personal", "phase": "usable"},
         {"target": "", "stakes": "personal", "phase": "usable"}, []),
        ("first sighting",
         {}, {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}, []),
    ]
    failures = 0
    for label, prev, cur, want in cases:
        got = state.vanished(prev, cur)
        ok = sorted(got) == sorted(want)
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  vanished: {label:28} {got}"
              f"{'' if ok else f'  (want {want})'}")
    note = state.vanished_note(["target"])
    ok = note == "target removed from STATE.md"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  vanished: note                     {note!r}")
    return 1 if failures else 0


def selftest_persist_values() -> int:
    """The stored snapshot carries the last non-empty value forward, so a
    vanished field keeps being reported until it comes back."""
    cases = [
        ("field vanishes, carried forward",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "", "stakes": "revenue", "phase": "usable"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}),
        ("field returns, current wins",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "2028-01-01", "stakes": "revenue", "phase": "usable"},
         {"target": "2028-01-01", "stakes": "revenue", "phase": "usable"}),
        ("never had one, stays empty",
         {"target": "", "stakes": "personal", "phase": ""},
         {"target": "", "stakes": "personal", "phase": ""},
         {"target": "", "stakes": "personal", "phase": ""}),
        ("first sighting, nothing to carry",
         {},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}),
    ]
    failures = 0
    for label, previous, current, want in cases:
        got = state.persist_values(previous, current)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  persist_values: {label:30} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0


def main() -> int:
    failures = 0
    failures += selftest_no_network_deps()
    failures += selftest_steps()
    failures += selftest_commits()
    failures += selftest_momentum()
    failures += selftest_debt()
    failures += selftest_ordering()
    failures += selftest_roles()
    failures += selftest_order_reason()
    failures += selftest_golden_order()
    failures += selftest_debt_never_orders()
    failures += selftest_rescue_selection()
    failures += selftest_debt_reason()
    failures += selftest_watched_values()
    failures += selftest_vanished()
    failures += selftest_persist_values()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
