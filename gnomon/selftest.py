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

    since, cut7, cut14 = ranking.commit_cutoffs(
        datetime.datetime(2026, 8, 21, 12, 0, tzinfo=datetime.timezone.utc)
    )
    ok = (since.startswith("2026-07-22") and cut7 == "2026-08-14"
          and cut14 == "2026-08-07")
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  commits: cutoffs               "
          f"{since} / {cut7} / {cut14}")
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

    # a near deadline outranks higher momentum when it is at risk
    cards = [_card("busy", momentum=200), _card("due", days_to_target=12, momentum=1)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["due", "busy"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: deadline beats momentum  {got}")

    # but a deadline visibly holding its pace does not take the top
    cards = [_card("busy", commits_7d=58, commits_30d=58, momentum=232),
             _card("ontrack", days_to_target=24, commits_7d=20,
                   commits_30d=30, momentum=90)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["busy", "ontrack"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: on-track date yields     {got}")

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

    # a stalled card is rescued wherever it ranks
    pool = [_card(f"r{i}", momentum=100 - i, commits_7d=20, commits_30d=40)
            for i in range(4)]
    pool.append(_card("rotting", momentum=1, commits_7d=0, commits_30d=9, age=12))
    got = roles(pool)
    ok = got["rotting"] == "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: stalled card rescued     {got.get('rotting')}")

    # debt alone earns nothing — this pool has no abandonment anywhere
    pool = [_card("visible", momentum=100, debt=9.0, commits_7d=30, commits_30d=60)] + \
           [_card(f"r{i}", momentum=50 - i, debt=9.0, commits_7d=10, commits_30d=20)
            for i in range(5)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: debt alone not rescued   {sorted(set(got.values()))}")

    # below the stall floor, no rescue slot at all
    pool = [_card(f"r{i}", momentum=50 - i, commits_7d=0, commits_30d=2, age=9)
            for i in range(8)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: stall floor respected    {sorted(set(got.values()))}")

    # parked is never rescued, even when genuinely stalled
    pool = [_card(f"r{i}", momentum=50 - i, commits_7d=10, commits_30d=20)
            for i in range(5)]
    pool.append(_card("parked", momentum=0, commits_7d=0, commits_30d=40,
                      age=12, phase="parked"))
    got = roles(pool)
    ok = got["parked"] != "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: parked never rescued     {got['parked']}")
    return 1 if failures else 0


def _commit(sha: str, day: str) -> dict:
    return {"sha": sha, "commit": {"committer": {"date": day + "T09:00:00Z"}}}


def selftest_code_commits() -> int:
    """Maintaining the board must not make a project look worked on."""
    failures = 0

    # The case this exists for: a dormant repo whose only commit is the
    # STATE.md header that was seeded into it.
    payload = [_commit("s1", "2026-08-17")]
    book = [_commit("s1", "2026-08-17")]
    got = ranking.code_commits(payload, book)
    ok = got == []
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  code: status-only repo is zero   {len(got)}")

    # Real work survives; the bundled status commit does not.
    payload = [_commit("a", "2026-08-22"), _commit("b", "2026-08-21"),
               _commit("s1", "2026-08-20")]
    book = [_commit("s1", "2026-08-20")]
    got = ranking.code_commits(payload, book)
    ok = [c["sha"] for c in got] == ["a", "b"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  code: work survives bookkeeping  "
          f"{[c['sha'] for c in got]}")

    # No bookkeeping at all changes nothing.
    got = ranking.code_commits(payload, [])
    ok = len(got) == 3
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  code: empty exclusion is a no-op {len(got)}")

    # Counting runs on the filtered list, so the seeded repo reads 0/0.
    payload = [_commit("s1", "2026-08-17")]
    c7, c30 = ranking.count_commits(ranking.code_commits(payload, payload), "2026-08-15")
    ok = (c7, c30) == (0, 0) and ranking.momentum(c7, c30) == 0
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  code: seeded repo counts 0/0     {(c7, c30)}")

    # The newest surviving commit dates the project, not the newest push.
    day = ranking.last_code_day([_commit("a", "2026-06-02"), _commit("b", "2026-07-11")])
    ok = day == "2026-07-11"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  code: last_code_day is newest    {day}")

    ok = ranking.last_code_day([]) == ""
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  code: no commits, no day         "
          f"{ranking.last_code_day([])!r}")
    return 1 if failures else 0


def selftest_age_floor() -> int:
    """A floor is a lower bound and must never be read as a measurement."""
    failures = 0
    cases = [
        ("measured span", (5, False), "5 days"),
        ("floored span", (30, True), "30+ days"),
        ("unknown span", (None, False), ""),
    ]
    for label, (age, floor), want in cases:
        got = ranking.quiet_span(age, floor)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  floor: {label:22} {got!r}")

    # The clause names the floor rather than inventing a precise age.
    card = _card("a", commits_7d=0, commits_30d=0, momentum=0, age=30)
    card["age_is_floor"] = True
    got = ranking.order_reason(card)
    ok = got == "no code in 30+ days"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  floor: clause names the floor    {got!r}")

    # A measured age keeps the old wording.
    card = _card("a", commits_7d=0, commits_30d=0, momentum=0, age=40)
    got = ranking.order_reason(card)
    ok = got == "quiet for 40 days"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  floor: measured age unchanged    {got!r}")

    # debt_reason agrees with the clause, and the footer says it once.
    card = _card("a", commits_7d=0, commits_30d=0, momentum=0, age=30)
    card["age_is_floor"] = True
    card["order_reason"] = ranking.order_reason(card)
    card["debt_reason"] = ranking.debt_reason(30, 14, "", None, True)
    line = ranking.why_line(card)
    ok = line == "no code in 30+ days" and line.count("30+") == 1
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  floor: span stated once          {line!r}")

    # A floored age still classifies and still accrues debt.
    ok = (ranking.classify("", "", 30, 14) == "stale"
          and ranking.debt(30, 14, "", None) > 2.0)
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  floor: still stale, still owed   "
          f"{ranking.classify('', '', 30, 14)}")
    return 1 if failures else 0


def selftest_why_line() -> int:
    """The footer must not state the same fact at both ends of the line."""
    def line(**kw):
        kw.setdefault("blocker", "")
        card = _card("a", **kw)
        card["order_reason"] = ranking.order_reason(card)
        card["debt_reason"] = ranking.debt_reason(
            card.get("age"), 14, card["blocker"], card.get("days_to_target")
        )
        return ranking.why_line(card)

    cases = [
        ("deadline keeps its debt",
         dict(days_to_target=11, commits_7d=2, commits_30d=25, momentum=31, age=5),
         "ships in 11 days \u00b7 momentum 31 - 2 this week, 25 this month"
         " \u00b7 quiet 5 days"),
        # order_reason already says overdue; debt_reason would say it again.
        ("overdue said once",
         dict(days_to_target=-3, commits_7d=1, commits_30d=9, momentum=12, age=3),
         "3 days overdue \u00b7 momentum 12 - 1 this week, 9 this month"),
        # A blocker is not a restatement of the date, so it survives.
        ("blocked overdue keeps blocked",
         dict(days_to_target=-3, commits_7d=1, commits_30d=9, momentum=12,
              age=3, blocker="waiting"),
         "3 days overdue \u00b7 momentum 12 - 1 this week, 9 this month"
         " \u00b7 blocked"),
        # The quiet fallback and debt_reason both report the same age.
        ("quiet said once",
         dict(days_to_target=21, commits_7d=0, commits_30d=0, momentum=0, age=40),
         "ships in 21 days \u00b7 quiet for 40 days"),
        ("unknown keeps its debt",
         dict(days_to_target=8, momentum=None, commits_7d=None,
              commits_30d=None, age=5),
         "ships in 8 days \u00b7 quiet 5 days"),
        ("momentum tier unchanged",
         dict(commits_7d=18, commits_30d=100, momentum=154, age=1),
         "momentum 154 - 18 this week, 100 this month \u00b7 quiet 1 days"),
    ]
    failures = 0
    for label, kw, want in cases:
        got = line(**kw)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  why: {label:28} {got}"
              f"{'' if ok else f'  (want {want})'}")

    # No fact may appear twice on one line.
    for label, kw, _ in cases:
        got = line(**kw)
        dupe = got.count("overdue") > 1 or got.count("quiet") > 1
        failures += dupe
        print(f"{'PASS' if not dupe else 'FAIL'}  why: no fact twice "
              f"{label:20} {got}")
    return 1 if failures else 0


def selftest_reason_matches_sort_key() -> int:
    """The sentence must state the number the sort actually uses."""
    failures = 0
    for c7, c30 in ((18, 100), (30, 33), (0, 9), (1, 1), (51, 51)):
        mom = ranking.momentum(c7, c30)
        card = _card("a", commits_7d=c7, commits_30d=c30, momentum=mom)
        sentence = ranking.order_reason(card)
        stated = sentence.split()[1] if sentence.startswith("momentum ") else ""
        ranked = -ranking.order_key(card)[2]
        ok = stated == str(mom) == str(ranked)
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  reason: states sort key "
              f"{c7}/{c30} -> {stated} (key {ranked})")

    # A quieter week outranking a busier one is explained, not merely restated.
    quiet = _card("q", commits_7d=18, commits_30d=100, momentum=154)
    busy = _card("b", commits_7d=30, commits_30d=33, momentum=123)
    ranks = sorted([quiet, busy], key=ranking.order_key)
    ok = ranks[0] is quiet and "100" in ranking.order_reason(quiet)
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  reason: inversion explained     "
          f"{ranking.order_reason(quiet)}")
    return 1 if failures else 0


def selftest_order_reason() -> int:
    cases = [
        # At risk: the deadline leads, then the momentum clause.
        ("overdue leads", _card("a", days_to_target=-3, commits_7d=1,
                                commits_30d=9, momentum=12),
         "3 days overdue \u00b7 momentum 12 - 1 this week, 9 this month"),
        ("ships today leads", _card("a", days_to_target=0, commits_7d=4,
                                    commits_30d=4, momentum=16),
         "ships today \u00b7 momentum 16 - 4 this week, 4 this month"),
        ("final week leads", _card("a", days_to_target=5, commits_7d=20,
                                   commits_30d=30, momentum=90),
         "ships in 5 days \u00b7 momentum 90 - 20 this week, 30 this month"),
        ("decelerating leads", _card("a", days_to_target=12, commits_7d=2,
                                     commits_30d=25, momentum=31),
         "ships in 12 days \u00b7 momentum 31 - 2 this week, 25 this month"),
        # Not at risk: momentum leads, the date follows without shouting.
        ("on track follows", _card("a", days_to_target=24, commits_7d=20,
                                   commits_30d=30, momentum=90),
         "momentum 90 - 20 this week, 30 this month \u00b7 ships in 24 days"),
        # A date beyond the window is not mentioned at all.
        ("distant date is silent", _card("a", days_to_target=200, commits_7d=20,
                                          commits_30d=30, momentum=90),
         "momentum 90 - 20 this week, 30 this month"),
        ("active", _card("a", commits_7d=51, commits_30d=51, momentum=204),
         "momentum 204 - 51 this week, 51 this month"),
        ("one commit", _card("a", commits_7d=1, commits_30d=1, momentum=4),
         "momentum 4 - 1 this week, 1 this month"),
        ("older work only", _card("a", commits_7d=0, commits_30d=9, momentum=9),
         "momentum 9 - 0 this week, 9 this month"),
        ("busier week, lower rank",
         _card("a", commits_7d=30, commits_30d=33, momentum=123),
         "momentum 123 - 30 this week, 33 this month"),
        ("quieter week, higher rank",
         _card("a", commits_7d=18, commits_30d=100, momentum=154),
         "momentum 154 - 18 this week, 100 this month"),
        ("deadline, activity unknown",
         _card("a", days_to_target=8, momentum=None, commits_7d=None,
               commits_30d=None),
         "ships in 8 days"),
        # A date approaching with no work at all is the most at-risk case
        # there is, and the pace arrow is silent there — so it must not be
        # mistaken for on track.
        ("deadline, genuinely quiet",
         _card("a", days_to_target=21, commits_7d=0, commits_30d=0,
               momentum=0, age=40),
         "ships in 21 days \u00b7 quiet for 40 days"),
        ("quiet", _card("a", commits_7d=0, commits_30d=0, momentum=0, age=94),
         "quiet for 94 days"),
        ("unknown", _card("a", momentum=None, commits_7d=None, commits_30d=None),
         "activity unknown"),
    ]
    failures = 0
    for label, card, want in cases:
        got = ranking.order_reason(card)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  reason: {label:24} {got!r}"
              f"{'' if ok else f'  (want {want!r})'}")
    return 1 if failures else 0


def selftest_at_risk() -> int:
    """Having a date is not the same as needing the top of the board."""
    failures = 0
    cases = [
        ("overdue", dict(days_to_target=-1, commits_7d=20, commits_30d=30,
                         momentum=90), True),
        ("final week", dict(days_to_target=7, commits_7d=20, commits_30d=30,
                            momentum=90), True),
        ("just past the final week, holding pace",
         dict(days_to_target=8, commits_7d=20, commits_30d=30, momentum=90), False),
        ("decelerating", dict(days_to_target=24, commits_7d=2, commits_30d=25,
                              momentum=31), True),
        ("on track", dict(days_to_target=24, commits_7d=20, commits_30d=30,
                          momentum=90), False),
        # Unknown must not be read as reassurance.
        ("unknown pace", dict(days_to_target=20, momentum=None,
                              commits_7d=None, commits_30d=None), True),
        ("no date", dict(commits_7d=20, commits_30d=30, momentum=90), False),
        # Dormant with a date approaching: the pace arrow is silent here.
        ("dated but dormant",
         dict(days_to_target=21, commits_7d=0, commits_30d=0, momentum=0), True),
        ("dated, activity unreadable",
         dict(days_to_target=21, commits_7d=None, commits_30d=None, momentum=1), True),
        ("date beyond the window",
         dict(days_to_target=200, commits_7d=2, commits_30d=25, momentum=31), False),
    ]
    for label, kw, want in cases:
        got = ranking.at_risk(_card("a", **kw))
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  risk: {label:38} {got}")

    faster = _card("fast", commits_7d=58, commits_30d=58, momentum=232)
    on_track = _card("dated", days_to_target=24, commits_7d=20,
                     commits_30d=30, momentum=90)
    ordered = sorted([on_track, faster], key=ranking.order_key)
    ok = ordered[0]["repo"] == "fast"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  risk: on-track yields the top     "
          f"{[c['repo'] for c in ordered]}")

    slowing = _card("dated", days_to_target=24, commits_7d=2,
                    commits_30d=25, momentum=31)
    ordered = sorted([slowing, faster], key=ranking.order_key)
    ok = ordered[0]["repo"] == "dated"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  risk: slowing takes it back       "
          f"{[c['repo'] for c in ordered]}")
    return 1 if failures else 0


def selftest_also_line() -> int:
    """The panel must always name what it is not showing."""
    failures = 0
    hero = _card("fast", project="Argus", commits_7d=58, commits_30d=58,
                 momentum=232)
    dated = _card("dated", project="anthonyvenitis.com", days_to_target=24,
                  commits_7d=20, commits_30d=30, momentum=90,
                  steps_done=5, steps_total=7)
    quiet = _card("quiet", project="Doukas", commits_7d=0, commits_30d=0,
                  momentum=0)
    nima = _card("b", project="Nima", commits_7d=22, commits_30d=40,
                 momentum=106)

    got = ranking.also_line([hero, dated, quiet])
    ok = got == ("On track", "anthonyvenitis.com ships in 24 days, 2 steps left")
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  also: dated card never vanishes   {got}")

    got = ranking.also_line([hero, quiet, nima])
    ok = got == ("Also", "Nima \u00b7 22/wk")
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  also: falls back to runner-up     {got}")

    got = ranking.also_line([hero])
    ok = got == ("", "")
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  also: silent with one card        {got}")

    got = ranking.also_line([hero, quiet])
    ok = got == ("", "")
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  also: silent when nothing to say  {got}")
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
    # Every repo in this fixture committed in the last 7 days, so nothing has
    # been walked away from and the rescue slot is correctly empty. Silence
    # when nothing is wrong is the behaviour, not a gap in the fixture.
    rescue = [c["repo"] for c in ordered if c["role"] == "rescue"]
    rescue_ok = rescue == []
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


def selftest_previous_week() -> int:
    """"2/wk" says nothing alone; "was 6/wk" is the deceleration stated."""
    failures = 0
    payload = ([_commit(f"n{i}", "2026-08-20") for i in range(2)]
               + [_commit(f"p{i}", "2026-08-12") for i in range(6)]
               + [_commit(f"o{i}", "2026-08-01") for i in range(4)])
    cut7, cut14 = "2026-08-15", "2026-08-08"
    prev = ranking.count_previous_week(payload, cut7, cut14)
    ok = prev == 6
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  prev: counts days 8-14        {prev}")

    c7, c30 = ranking.count_commits(payload, cut7)
    # The windows must not overlap or double-count.
    ok = (c7, prev, c30) == (2, 6, 12)
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  prev: windows do not overlap  {(c7, prev, c30)}")

    ok = ranking.count_previous_week([], cut7, cut14) == 0
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  prev: empty payload is zero   0")

    since, c7cut, c14cut = ranking.commit_cutoffs(
        __import__("datetime").datetime(2026, 8, 22, 12, 0, 0))
    ok = c7cut == "2026-08-15" and c14cut == "2026-08-08" and since.startswith("2026-07-23")
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  prev: cutoffs                 {(c7cut, c14cut)}")
    return 1 if failures else 0


def selftest_week_buckets() -> int:
    """Four whole weeks, no commit counted twice and none lost."""
    failures = 0
    import datetime as _dt
    edges = ranking.week_edges(_dt.datetime(2026, 8, 22, 12, 0, 0))
    ok = edges == ["2026-07-25", "2026-08-01", "2026-08-08", "2026-08-15"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  weeks: edges are four Saturdays {edges}")

    payload = ([_commit(f"a{i}", "2026-08-20") for i in range(3)]
               + [_commit(f"b{i}", "2026-08-12") for i in range(5)]
               + [_commit(f"c{i}", "2026-08-05") for i in range(2)]
               + [_commit(f"d{i}", "2026-07-29") for i in range(4)]
               + [_commit("old", "2026-07-01")])
    got = ranking.week_buckets(payload, edges)
    ok = got == [4, 2, 5, 3]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  weeks: buckets oldest first    {got}")

    # Everything inside 28 days is counted exactly once; older is dropped.
    ok = sum(got) == len(payload) - 1
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  weeks: nothing double-counted  {sum(got)}")

    # The newest bucket must include today, not fall off the open end.
    ok = ranking.week_buckets([_commit("t", "2026-08-22")], edges) == [0, 0, 0, 1]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  weeks: today lands in this wk  "
          f"{ranking.week_buckets([_commit('t', '2026-08-22')], edges)}")

    ok = ranking.week_buckets([], edges) == [0, 0, 0, 0]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  weeks: empty payload is zeros  ")

    # Board totals sum every reporting repo and ignore the silent ones.
    cards = [_card("a", weeks=[1, 2, 3, 4]), _card("b", weeks=[10, 0, 0, 1]),
             _card("dark")]
    got = ranking.board_weeks(cards)
    ok = got == [11, 2, 3, 5]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  weeks: board totals            {got}")

    ok = ranking.board_weeks([_card("dark"), _card("dark2")]) == []
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  weeks: nothing reporting, empty")
    return 1 if failures else 0


def selftest_activity_readout() -> int:
    """The reading must be earned; a flat month is not a ranking."""
    failures = 0
    cases = [
        ("quietest", [214, 168, 190, 163], ("Your quietest week in four", 184)),
        ("busiest", [214, 168, 190, 231], ("Your busiest week in four", 201)),
        # Four near-identical weeks: calling one of them the quietest is true
        # and misleading at once.
        ("flat month", [180, 182, 179, 181], ("Holding steady", 180)),
        ("below average", [100, 50, 60, 70], ("Below your four-week average", 70)),
        # 210/4 is 52.5; Python rounds half to even, so 52.
        ("above average", [100, 20, 30, 60], ("Above your four-week average", 52)),
        ("no activity at all", [0, 0, 0, 0], ("", 0)),
        ("nothing reporting", [], ("", 0)),
    ]
    for label, weeks, want in cases:
        got = ranking.activity_readout(weeks)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  readout: {label:20} {got}"
              f"{'' if ok else f'  (want {want})'}")

    # The sentence must never contradict the bars it sits above.
    for weeks in ([214, 168, 190, 163], [214, 168, 190, 231], [5, 5, 5, 400]):
        sentence, _ = ranking.activity_readout(weeks)
        if "busiest" in sentence:
            ok = weeks[-1] == max(weeks)
        elif "quietest" in sentence:
            ok = weeks[-1] == min(weeks)
        else:
            ok = True
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  readout: agrees with bars {weeks} -> {sentence!r}")
    return 1 if failures else 0


def selftest_hero_verdict() -> int:
    """The verdict must agree with the arrow rendered beside it."""
    failures = 0
    cases = [
        ("overdue", dict(days_to_target=-3), "overdue"),
        ("slowing into a deadline",
         dict(days_to_target=11, commits_7d=2, commits_30d=25),
         "slowing into a deadline"),
        ("accelerating into a deadline",
         dict(days_to_target=11, commits_7d=20, commits_30d=30),
         "accelerating into a deadline"),
        # Below the pace floor the arrow is silent, so the verdict must be too.
        ("deadline, pace below floor",
         dict(days_to_target=11, commits_7d=1, commits_30d=4), "shipping soon"),
        ("fastest right now",
         dict(commits_7d=58, commits_30d=58, momentum=232), "moving fastest right now"),
        ("active but steady",
         dict(commits_7d=10, commits_30d=43, momentum=73), "your most active project"),
        ("nothing to say",
         dict(commits_7d=0, commits_30d=0, momentum=0), ""),
        ("unknown says nothing",
         dict(commits_7d=None, commits_30d=None, momentum=None), ""),
    ]
    for label, kw, want in cases:
        got = ranking.hero_verdict(_card("a", **kw))
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  verdict: {label:28} {got!r}"
              f"{'' if ok else f'  (want {want!r})'}")

    # The verdict and the pace arrow are driven by one function, so they
    # cannot disagree.
    for c7, c30 in ((2, 25), (20, 30), (1, 4), (10, 43)):
        card = _card("a", commits_7d=c7, commits_30d=c30, days_to_target=11)
        trend = ranking.pace(card)
        verdict = ranking.hero_verdict(card)
        ok = (("slowing" in verdict) == (trend == "down")
              and ("accelerating" in verdict) == (trend == "up"))
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  verdict: agrees with pace {c7}/{c30}  "
              f"{trend or 'flat'} -> {verdict!r}")
    return 1 if failures else 0


def selftest_stall() -> int:
    """Absence of work is not debt; work that stopped is."""
    failures = 0
    cases = [
        ("stalled", dict(commits_7d=0, commits_30d=18), 18),
        ("still moving", dict(commits_7d=5, commits_30d=20), 0),
        # The case that made this exist: a seasonal project, correctly asleep.
        ("dormant all month", dict(commits_7d=0, commits_30d=0), 0),
        ("below the floor", dict(commits_7d=0, commits_30d=2), 0),
        ("exactly the floor", dict(commits_7d=0, commits_30d=3), 3),
        # Unknown is not zero, and it is not a stall either.
        ("unknown", dict(commits_7d=None, commits_30d=None), None),
    ]
    for label, kw, want in cases:
        got = ranking.stall(_card("a", **kw))
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  stall: {label:22} {got}"
              f"{'' if ok else f'  (want {want})'}")

    got = ranking.stall_reason(_card("a", commits_7d=0, commits_30d=18, age=11))
    ok = got == "18 commits, then nothing for 11 days"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  stall: names the abandonment  {got!r}")

    ok = ranking.stall_reason(_card("a", commits_7d=4, commits_30d=18, age=1)) == ""
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  stall: moving has no reason   "
          f"{ranking.stall_reason(_card('a', commits_7d=4, commits_30d=18, age=1))!r}")
    return 1 if failures else 0


def selftest_rescue_selection() -> int:
    """Rescue surfaces the biggest abandonment, and nothing else."""
    failures = 0

    def roles(pool):
        ordered = sorted(pool, key=ranking.order_key)
        ranking.assign_roles(ordered)
        return {c["repo"]: c["role"] for c in ordered}

    pool = [_card(f"r{i}", momentum=100 - i, commits_7d=20, commits_30d=40)
            for i in range(4)]
    pool += [
        _card("small-stall", momentum=10, commits_7d=0, commits_30d=5, age=9),
        _card("big-stall", momentum=9, commits_7d=0, commits_30d=40, age=20),
        _card("mid-stall", momentum=8, commits_7d=0, commits_30d=12, age=9),
    ]
    got = roles(pool)
    rescues = [r for r, role in got.items() if role == "rescue"]
    ok = rescues == ["big-stall"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  rescue: biggest abandonment     {rescues}")

    # A card ranked high is still rescuable — the old rank-5 rule is gone.
    pool = [_card("leader", momentum=100, commits_7d=30, commits_30d=60),
            _card("stalled-2nd", momentum=50, commits_7d=0, commits_30d=50, age=8)]
    got = roles(pool)
    ok = got["stalled-2nd"] == "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  rescue: rank does not disqualify {got}")

    # Ties go to the warmer stall.
    pool = [_card("lead", momentum=100, commits_7d=30, commits_30d=60),
            _card("cold", momentum=10, commits_7d=0, commits_30d=20, age=26),
            _card("warm", momentum=9, commits_7d=0, commits_30d=20, age=9)]
    got = roles(pool)
    ok = got["warm"] == "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  rescue: warmer stall wins ties  "
          f"{[r for r, x in got.items() if x == 'rescue']}")

    # Nothing stalled means no rescue card at all.
    pool = [_card(f"r{i}", momentum=50 - i, commits_7d=10, commits_30d=20)
            for i in range(6)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  rescue: silent when none stalled "
          f"{sorted(set(got.values()))}")

    # The seasonal case: dormant projects are never rescued.
    pool = [_card("lead", momentum=100, commits_7d=30, commits_30d=60)]
    pool += [_card(f"asleep{i}", momentum=0, commits_7d=0, commits_30d=0,
                   age=30, debt=2.14) for i in range(3)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  rescue: dormant is never rescued "
          f"{sorted(set(got.values()))}")

    # Parked, blocked and deadline-tier cards are all excluded. The lead card
    # is given the nearer target so a deadline-tier candidate cannot be
    # "excluded" merely by becoming the hero — that would pass for the wrong
    # reason and prove nothing about the rule under test.
    for label, extra in (("parked", dict(phase="parked")),
                         ("blocked", dict(blocker="vendor key")),
                         ("deadline tier", dict(days_to_target=5))):
        pool = [_card("lead", momentum=100, commits_7d=30, commits_30d=60,
                      days_to_target=1),
                _card("excluded", momentum=9, commits_7d=0, commits_30d=40,
                      age=12, **extra)]
        got = roles(pool)
        ok = got["excluded"] not in ("rescue", "hero")
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  rescue: {label:16} excluded  "
              f"{got['excluded']}")

    # Unknown activity is not a stall.
    pool = [_card("lead", momentum=100, commits_7d=30, commits_30d=60),
            _card("dark", momentum=None, commits_7d=None, commits_30d=None)]
    got = roles(pool)
    ok = got["dark"] != "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  rescue: unknown is not a stall  {got['dark']}")
    return 1 if failures else 0


def selftest_debt_never_rescues() -> int:
    """Debt is essentially age, and age surfaces what is ignored on purpose.

    It once chose the rescue card, which meant a seasonal project asleep all
    summer outranked a project that died mid-flight. Debt labels a card now;
    it must never select one again.
    """
    failures = 0
    for debt in (0.0, 1.0, 5.0, 99.0):
        pool = [_card("lead", momentum=100, commits_7d=30, commits_30d=60),
                # Huge debt, no abandonment: asleep on purpose.
                _card("idle", momentum=0, commits_7d=0, commits_30d=0,
                      age=90, debt=debt),
                # Modest debt, real abandonment: died mid-flight.
                _card("stalled", momentum=8, commits_7d=0, commits_30d=8,
                      age=9, debt=0.5)]
        ordered = sorted(pool, key=ranking.order_key)
        ranking.assign_roles(ordered)
        picked = [c["repo"] for c in ordered if c["role"] == "rescue"]
        ok = picked == ["stalled"]
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  rescue: debt {debt:>5} never wins   {picked}")
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
    failures += selftest_at_risk()
    failures += selftest_also_line()
    failures += selftest_reason_matches_sort_key()
    failures += selftest_why_line()
    failures += selftest_code_commits()
    failures += selftest_age_floor()
    failures += selftest_golden_order()
    failures += selftest_debt_never_orders()
    failures += selftest_previous_week()
    failures += selftest_week_buckets()
    failures += selftest_activity_readout()
    failures += selftest_hero_verdict()
    failures += selftest_stall()
    failures += selftest_rescue_selection()
    failures += selftest_debt_never_rescues()
    failures += selftest_debt_reason()
    failures += selftest_watched_values()
    failures += selftest_vanished()
    failures += selftest_persist_values()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
