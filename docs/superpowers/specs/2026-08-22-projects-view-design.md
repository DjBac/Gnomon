# Projects view in Argus — design

Written 2026-08-22. Approved by Anthony from the mockups in this session.

Anthony has decided Argus absorbs Gnomon entirely: the Home Assistant add-on is
retired and the board becomes a view inside Argus. Argus's session has confirmed
it goes into `ROADMAP.md` **ahead of** the existing programme.

The work decomposes into three specs. **This is the first: the view.** The
collector and the retirement follow, in that order. Anthony chose to design the
view first because what it must show determines what the collector must produce.

Background on the system being absorbed is in `docs/ABSORPTION-BRIEF.md`.

---

## 1 · The question the view answers

**What should I work on now?**

Not "what is the state of my projects" — that is a dashboard, and eight releases
of Gnomon established that a dashboard makes you assemble the answer yourself
from a hero card, a badge and an arrow. On a phone at 7am that is one step too
many.

The view answers in a sentence, then shows the evidence.

Every other decision below follows from that. When something here is ambiguous,
resolve it by asking which option gets to the answer faster.

---

## 2 · The organising idea: a verdict that can abstain

Argus's best existing design decision is that **the Eye's score abstains when
blind**. Projects adopts it.

The view leads with a **verdict** — one sentence naming what to work on and why.
A verdict is a claim, so it must be able to decline to make one. Three forms:

| Form | When | Example |
|---|---|---|
| **Directive** | Something is at risk or clearly leads | "Work on anthonyvenitis.com — it ships in 11 days and it will not make it" |
| **Calm** | Nothing urgent, nothing stalled | "Nothing is urgent" + where the momentum is |
| **Abstaining** | Too little is known to rank honestly | "Not enough to advise — activity unreadable for 7 of 12 repositories" |

**The abstaining form is mandatory, not a nicety.** "Unknown is not zero" has
caused three shipped bugs in this project. A ranking computed over mostly-null
activity is a guess wearing a sentence's clothing.

**Abstention threshold:** abstain when activity is unknown for more than half of
the reporting repositories, or when the top-ranked card's own activity is
unknown. Both conditions are computed server-side and delivered as a decided
verdict — the view renders it, it does not derive it.

**The verdict should not be a new shape.** Argus's Eye already carries a claim
plus the subtraction behind it: a score with `deductions`, each naming the tile
it came from, on the principle that a score nobody can interrogate is an opinion
with a typeface. A verdict about a project is the same idea — the sentence is
the claim, the facts beneath it are the deductions. If `Verdict` can be that
shape rather than a second one, both improve.

---

## 3 · Structure

Top to bottom, single column, stacking to one column below 980px:

1. **Verdict block** — the sentence, why, and the facts justifying it
2. **Attention band** — stalls, long-standing blockers, dormancy. Absent when empty
3. **Ranked list** — every project, in order, with 12-week history and steps/week
4. **Insight tiles** — activity over 12 weeks, stakes drift, focus

A **Projects line on Overview** carries the verdict's headline and links here.
That line is what preserves the daily habit the HA sidebar currently provides;
it is not optional decoration.

---

## 4 · What the view shows, precisely

### 4.1 Verdict block

- The sentence (server-decided; see §2)
- The current step of the named project, verbatim from `STATE.md`
- Up to four facts: days to target, steps remaining, rate with the previous
  week beside it (`2/wk ↓ · was 6/wk`), steps per week
- **Forecast** when computable (§5.1)
- **Slip history** when the target has moved (§5.2)

The rate must always name its comparison. `2/wk` alone says nothing; `2/wk, was
6/wk` is the deceleration stated. This was the whole content of release 0.5.8
and must not be lost in translation.

### 4.2 Attention band

One card per condition, each naming the project and what is at stake. Conditions:
stalled (§5 of the brief), blocked-for (§5.3), dormant count. **Renders nothing
when nothing qualifies** — most of the time, which is correct for an alarm.

### 4.3 Ranked list

Columns: position, project, current step, 12-week sparkline, **steps per week**.

Steps per week replaces momentum as the visible right-hand column. Momentum
measures motion; steps per week measures progress, and progress is the honest
unit. Momentum still does the sorting and remains available on the project's own
page.

Dormant and parked rows dim, using `--stale-dim`.

### 4.4 Insight tiles

Activity over 12 weeks with its reading (§5 below), stakes drift (§5.4), focus
(§5.5).

---

## 5 · The six features history unlocks

None of these are computable from a single poll. All of them require Argus's
`chronicle.py`, `events/` store and metrics `series`. Each has an explicit
abstention condition — a feature that cannot compute must say nothing rather
than show a zero.

### 5.1 Forecast

**Steps per week**, measured from recorded step completions, projected against
steps remaining and the target date.

> At 0.6 steps a week, 2 steps left finishes around 15 September — 13 days past
> the target. Based on 9 step completions since 21 July.

Commits-per-step was refused during Gnomon's development because there is no
honest exchange rate between them. Steps per week is a directly measured unit,
which is what makes this legitimate now and illegitimate before.

**Abstains** when fewer than 4 step completions are recorded for the project, or
when the window is shorter than 3 weeks. The sample size is always stated.

### 5.2 Slip history

The sequence of values a `target` has held. `15 Aug → 26 Aug → 2 Sep`, with a
count when it exceeds one move. Only a store can know this.

**Abstains** when the target has never changed since first observation.

### 5.3 Blocked-for

How long a non-empty `blocker` has held the same text. A blocker is external by
definition, so duration is the signal: 23 days means escalate, not wait.

**Abstains** when no blocker is set. Resets when the text changes.

### 5.4 Stakes drift

The `stakes` split of commits, over time rather than this week alone.

> Revenue has been under 15% for six weeks running.

**Abstains** with fewer than 4 complete weeks of history.

### 5.5 Focus

Distinct projects receiving code commits this week, against last week.

> 6 projects touched, up from 3 last week. More spread, less depth.

**Abstains** when either week's activity is incomplete.

### 5.6 Since you were away

What changed since the last visit: steps completed, projects that stalled,
targets that slipped. Borrows the Eye's existing stance — it appears after an
absence and then disappears. Not a feed.

**Abstains** when the gap is under 24 hours, or nothing changed.

---

## 5A · Invariants, stated as truth claims

Argus's session made a correction worth recording: several of Gnomon's
invariants are not instructions about what to show, they are claims about what
is true — and Argus **already enforces each one's twin** under a different name,
arrived at independently. They should be *mapped*, not ported. Two dialects of
one rule is how drift begins.

| Truth claim (Gnomon) | Existing Argus mechanism |
|---|---|
| Absence of measurement is not a measurement of zero | A series with no history renders the words "no history", never a flat line at zero — a flat line claims something was measured and found to be nothing |
| A lower bound must never be rendered as precise | `Cell.status == unknown` means *reported, not judged*: a number with no band takes no colour and implies no verdict |
| One fact is stated once | Chronicle suppresses the state-pair spine on `transition` rows because the message already narrates it |
| Feeding a measurement system must not alter what it measures | No twin yet — see below |

The fourth has no counterpart in Argus and is a genuine finding. Argus has met
the same *family* (a heartbeat pinging a shared dead-man's-switch from two
instances, so a healthy check masked a dark site) but has no general mechanism.
The `path=STATE.md` subtraction is therefore a **stated requirement of the
collector spec**, not something its author is expected to rediscover.

**Each invariant gets a test that fails when it is violated, written before the
collector.** Gnomon's three `selftest_debt_*` tests exist because the mistake had
already been made; the point is to acquire that protection without repeating the
mistakes first.

---

## 6 · Where a push lands

Argus can interrupt; Gnomon never could. This is the single largest capability
gain and it is in scope for this view's design, though the alert rules
themselves belong to the collector spec.

Two conditions justify a push: **a project stalls** (`stall > 0` newly true), and
**a dated project's forecast crosses its target**. Both land in a per-project
focus page following the Incident stance — "a change of stance, not a panel added
to the same page" — showing what was abandoned, how long ago, steps remaining,
and the `## Open` section of that repo's `STATE.md` as the runbook.

The runbook is not invented: it is the diagnosis Anthony already writes for
himself.

---

## 6A · Sequencing — decided

Anthony ruled directly to Argus's session: **"confirming the absorption, gnomon
first, then the argus tokens then the next task."** Recorded in Argus's
`ROADMAP.md` at commit `173c99e`, placed ahead of the numbered programme with
the existing numbers deliberately unchanged, because `CLAUDE.md` tells every
future session that "Milestone N" is enough to locate a route.

The concern that Projects would be built on patterns already agreed to be wrong
was raised and **overruled on timing**. It is not re-litigated here.

The mitigation, agreed with Argus's session, is that **Projects is built to the
agreed pattern rather than the current one** — the design decisions already
exist, so the newest view demonstrates the target that the retrofit will later
drag the four older views toward. Three requirements carry that (§7.8, §7.9 and
§7.1), and they turn the ordering from a cost into an advantage: Projects
becomes the reference, not the fifth thing to fix.

---

## 7 · Design conformance — requirements, not intentions

Anthony's requirement is that the view follow Argus's design completely, and keep
following it when Argus's design changes. That cannot be a promise; it has to be
a mechanism.

1. **No literal values.** Every colour, radius, size, duration and shadow is a
   `var(--…)` reference. No exceptions, including "just this one gradient".
2. **`data-theme="daylight"` on the view's root element**, as `views/Overview`
   and `views/Gate` do. The `--pill-*` families are defined inside the daylight
   block and resolve to nothing outside a daylight subtree.
3. **Reference `--pill-*` only, never a copied approximation.** Argus's session
   reports that the four drifted views hardcode their own approximations of the
   crit and warn pill colours; the blast radius when a designer revisits them is
   therefore larger than a token grep suggests. Projects must not become a fifth
   place to fix.
4. **Treat `--pill-{crit,warn,stale}-*` as provisional.** They are marked
   `/* DERIVED */` — extrapolated rather than drawn. Nothing may depend on their
   exact values; only on their roles.
5. **Reuse `Tile`, `Ring` and `Sparkline`** rather than restyling them. If `Tile`
   changes, Projects changes for free. That is the conformance mechanism doing
   its job.
6. **The verdict block ships as `components/Verdict/`**, not as page-local CSS,
   so it enters Argus's system and other views can use it.
7. **No exhaustive `Record<Status, …>` maps.** `Status` is gaining an "off"
   value; `Tile.tsx`'s `PILL_TEXT` is exactly that shape and will break.
8. **If Projects shows status in a table, use dot + word**, not the current
   dot-only cell, which is the direction the console is moving.
9. **Do not import `Register.module.css` for page chrome.** It currently doubles
   as the console page stylesheet; that split is a queued defect.
10. **The automated colour check applies to this view from its first commit.**
    Argus owns that checker — Anthony assigned it there. Gnomon has no such check
    to contribute: what it has is a rule in prose and a hand-run grep with a
    positional carve-out.

---

## 8 · Data contract

The view renders; it judges nothing. Every judgment below arrives decided from
the backend, matching how `Compute.tsx` already works.

Per board: `verdict` (form, sentence, subject), `weeks[12]`, `activity_readout`,
`average`, `stakes_drift`, `focus`, `since_away[]`.

Per project: `project`, `repo`, `state`, `phase`, `stakes`, `steps_done`,
`steps_total`, `current_step`, `momentum`, `commits_7d`, `commits_prev7`,
`commits_30d`, `weeks[12]`, `steps_per_week`, `stall`, `blocked_for_days`,
`days_to_target`, `target_history[]`, `age`, `age_is_floor`, `role`.

**Nullable means unknown, and unknown is not zero.** Any numeric field may be
`null`; the view renders absence, never a substituted zero.

**Argus ranks itself, deliberately.** Argus's own `STATE.md` carries the same
six-field header, so Argus appears as a row among the projects. This is
intentional and should not be reported as a defect. It is worth naming because
it is the self-reference family again: Argus's status file is written by the
sessions that build Argus, so its own row is the one row whose freshness it can
influence. Harmless — the `path=STATE.md` subtraction already prevents status
commits from counting as work, which is exactly the mechanism that makes it
harmless rather than merely unlikely to matter.

---

## 9 · Testing

- The 188 assertions in `selftest.py` port with `ranking.py` and `state.py`.
  Port `selftest_debt_never_orders` and `selftest_debt_never_rescues` first —
  they encode decisions rather than behaviour, and both exist because the
  mistake was already made.
- Every abstention condition in §5 gets a test asserting **silence**, not a zero.
- A test asserting the verdict's stated subject is the project the ranking
  actually selected, mirroring Gnomon's rule that a board must not sort on a
  number it never displays.
- The colour check (§7.10) runs against this view in CI.

---

## 10 · Phasing

This is more than one release. Proposed order, each independently shippable:

**Phase 1** — verdict (all three forms), ranked list, attention band, Overview
line. No history required; computable from a single poll.

**Phase 2** — the history features (§5.1–5.5) as the store accumulates. They
abstain until they can compute, so shipping them early is safe and they light up
on their own.

**Phase 3** — pushes and the project focus page (§6), plus "since you were
away" (§5.6).

The 12-week sparklines are empty at launch and fill over twelve weeks. **The
empty state must be designed deliberately**, not left as a blank cell.

---

## 11 · Open questions

- Where the vanished-field memory currently in `/data/gnomon-seen.json` lives in
  Argus.
- Whether step completions are recorded by diffing `STATE.md` per poll, or
  whether Chronicle already offers a suitable event shape. This determines
  whether §5.1 is cheap or expensive.
- Where the vanished-field memory currently in `/data/gnomon-seen.json` lives.
- Whether step completions are recorded by diffing `STATE.md` per poll, or
  whether Chronicle already offers a suitable event shape.

---

## 12 · Ownership

Settled with Argus's session:

- **This side owns the domain** — ranking semantics, `momentum` / `at_risk` /
  `stall`, the `STATE.md` contract, and every invariant stated as a truth claim.
  That knowledge exists nowhere else and would otherwise be guessed at.
- **Argus owns rendering, the component landscape, and conformance** — including
  translating each invariant into the mechanism that already enforces its twin,
  and the `Verdict` component, because it enters a system other views will reach
  for.
