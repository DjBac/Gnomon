# HANDOFF — read me first

Written 2026-08-22, end of the session that shipped 0.4.0 and 0.5.0.
Current release: **0.5.8**, on `main` and pushed.

## What Gnomon is

A Home Assistant add-on that polls a list of GitHub repositories, reads the YAML
front-matter block at the top of each repo's `STATE.md`, and serves a
single-page board over HA ingress. Read almost entirely on an iPhone, in the HA
Companion App.

**Read-only.** Editing from the panel is deliberately out of scope.

**The governing rule:** facts come from the GitHub API, judgments come from
`STATE.md`. Anything derivable is derived. Nothing that can rot by hand is
stored by hand.

## Where the code is

| File | Lines | Responsibility | Imports |
|---|---|---|---|
| `gnomon/state.py` | 169 | Parse `STATE.md` — front-matter, steps, dates, normalisation, vanished-field diffing | `yaml`, stdlib |
| `gnomon/ranking.py` | 473 | Momentum, debt, ordering, roles, human-readable reasons | stdlib only |
| `gnomon/github.py` | 87 | The four API calls and their error notes | `aiohttp` |
| `gnomon/app.py` | 405 | Options, card assembly, `/data` persistence, HTTP routes | all of the above |
| `gnomon/selftest.py` | 1123 | The entire test suite | `state` + `ranking` only |
| `gnomon/www/index.html` | 1288 | The whole panel — tokens, layout, render | none |

**`state.py` and `ranking.py` must never import `aiohttp`.** That is what lets
`python3 gnomon/selftest.py` run outside the container. A test in `selftest.py`
enforces it — keep it passing.

## How to test

```bash
python3 gnomon/selftest.py          # 188 assertions, must exit 0
```

`aiohttp` is NOT installed on Anthony's Mac, so `app.py` and `github.py` cannot
be imported or run locally — verify them with
`python3 -c "import ast; ast.parse(open('gnomon/app.py').read())"`.

**The panel has no committed test.** It is verified with hand-written DOM-stub
harnesses under Node, kept in a scratchpad and never committed. If you change
`index.html`, write one: extract the `<script>` block, stub `createElement` /
`createElementNS` / `appendChild` / `className` / `textContent` / `setAttribute`
/ `classList` / `style.setProperty` / `getElementById`, drive `render()`, and
walk the resulting tree.

**A browser cannot be opened** — localhost is blocked by policy in this
environment. Everything visual is verified by static inspection, contrast
arithmetic, and the DOM stub. Anthony is the only one who can look at it.

## How the board works

### Ordering — two tiers

1. **Deadline, but only when at risk.** Having a date is not the same as
   needing the top of the board. `ranking.at_risk` puts a dated card first when
   it is overdue, inside its final 7 days, dormant, or visibly decelerating.
   Soonest first within the tier.

   **Only a project we can positively see holding its pace is demoted.**
   Unreadable activity, zero commits in the window, and a silent pace arrow all
   count as at risk — the arrow is deliberately mute below ten commits a month,
   which is exactly where a dormant project with a date approaching would hide.
   A dated card that yields the top slot is never lost: `ranking.also_line`
   names it under the now panel as `On track · X ships in N days`.
2. **Momentum.** Everything else, descending:
   `momentum = (commits in 7d x 3) + commits in 30d`

Ties break on `stakes` (revenue, product, personal), then repo name.

Momentum counts commits on the **default branch only** — the commits call sends
no `sha`, so unmerged feature-branch work does not raise it.

**Status commits do not count as work.** A second commits call with
`path=STATE.md` lists the bookkeeping commits, and `ranking.code_commits`
subtracts them by SHA. Without this, feeding Gnomon made every project look
alive: a dormant repo's one seeded header read as `1/wk` and `fresh`. A commit
that bundles STATE.md with real code is dropped too, so an active project
undercounts by roughly one commit per session — deliberate, because the
alternative is a dormant project reporting activity it does not have.

**Age is days since the last code commit, not days since the last push.**
`pushed_at` is repo-level: any push, any branch, any file. When no code commit
appears anywhere in the 30-day window, `age` is set to 30 with
`age_is_floor` true, and every string says `30+ days` — a lower bound, never a
measurement. `card["updated"]` still carries `pushed_at`, which remains a true
fact about the repo, just not a fact about work.

### Debt marks a card and never moves one

```
debt = age / stale_days  +  1.5 if blocked  +  2.0 if overdue
```

Debt is never read by the sort key. There is a test, `selftest_debt_never_orders`,
that exists solely to defend this — it was added because a mutation injecting
debt as a tiebreak passed the entire suite unnoticed.

### Roles

- **hero** — top card, leads with its `[>]` step as the largest text on screen.
  Suppressed only when all three hold: no `[>]`, no target within 30 days, and
  momentum exactly `0`. **Unknown momentum does not suppress it.**
- **rescue** — at most one, chosen by **stall**, never by debt:

  ```
  stall = commits_30d  when commits_7d == 0 and commits_30d >= 3, else 0
  ```

  Read it as commits walked away from. Absence of work is not debt; work that
  *stopped* is — a project with thirty commits and then silence has thirty
  commits of loaded context sitting there. Excluded: `parked`, blocked (a
  blocker is not fixed by working harder), and anything in the deadline tier
  (already at the top of the board). Rank does not disqualify. Ties go to the
  warmer stall, which is cheaper to restart. Renders nothing when nothing
  qualifies, which is most of the time and is correct.

  **Debt no longer selects anything.** It is essentially age, and the
  longest-untouched projects are the ones untouched on purpose — driving rescue
  from it meant a seasonal tool asleep all summer outranked a project that died
  mid-flight. `selftest_debt_never_rescues` defends this, in the same spirit as
  `selftest_debt_never_orders`.
- **tail** — everything else, in sort order.

### The rule that keeps being violated

**Unknown is not zero.** `commits_7d` / `commits_30d` / `momentum` are `null`
when the activity call failed. That is different from a genuinely quiet project,
and three separate bugs in this project came from collapsing them. Any new code
touching activity must preserve the distinction.

## The panel

**One "now" panel** at the top, then optional rescue, then tail rows carrying
activity bars and pace arrows.

The now panel replaced the separate summary panel and hero card in 0.5.5. It
leads with the instruction — `Work on this now`, then the `[>]` step as the
largest text on screen — then the project and `ranking.hero_verdict` in words,
then progress, then three facts: days until it ships, steps left, and the rate
*with last week's rate beside it* (`2/wk ↓ · was 6/wk`). Then one "also" line
naming what the panel is *not* showing — a dated project that is on track, or
failing that the runner-up, so the board never hides where the energy is. The week is demoted to
a strip at the foot: total commits, then triage chips counting what is shipping
soon, stalled, and asleep. A chip with a count of zero is not drawn.

The reasoning: every number in the old summary panel was true and none of them
changed what you do next. It was a scoreboard in the most valuable position on
the screen. The `#summary` host div stays, display-none, so the load path is
unchanged.

**The stats panel leads the board** as of 0.5.8 — Anthony's call: the month's
shape sets the context, then the instruction answers it. Order is
`stats → now → rescue → tail`, and the DOM harness asserts it.

The now panel's foot no longer repeats the week's commit total, which the stats
panel above now owns; what remains there is the triage, which nothing else
reports. When *no* repo reports activity at all, the stats panel says
**"Activity unknown"** rather than rendering nothing — a board that draws
nothing there reads as a quiet month rather than a failed call.

The stats panel itself, added in 0.5.7 and now first. It leads with the reading and shows the arithmetic under it:

```
ACTIVITY
Your quietest week in four · 163 commits
214   168   190   163
4 wks ago  3 wks  last wk  this wk
Four-week average 184
```

Four 7-day buckets from the commit payload already fetched — 28 days inside a
30-day window, so every bar is a full week and the oldest two days go unused.
No extra API call. `ranking.activity_readout` ranks the current week against
the other three, and a spread under 15% of the average returns **"Holding
steady"** rather than a ranking: calling one of four near-identical weeks the
quietest is true and misleading at once.

The completion ring and stakes split came back with it — the ring now carries
`role="img"`, and the stakes key gained colour swatches, so two entries from
`known-issues.md` are closed. Nothing repeats: the sentence gives the meaning,
the bars give the counts, the average gives the baseline.

`order_reason` returns a string, not a tuple: `order_badge` was orphaned when
the panels merged and is gone, along with the `.badge` CSS.

`ranking.pace` was added so the verdict cannot disagree with the arrow drawn
beside it — a test asserts they move together. `commits_prev7` comes from the
same commits payload, no extra call.

**Pace:** `ratio = commits_7d / (commits_30d / 4.3)`, up at `>= 1.25`, down at
`<= 0.6`, nothing between — and **suppressed entirely below 10 commits in 30
days**, because under that floor a single commit reads as a 4.3x surge.

**Two palettes**, both taken from `~/Code/argus/design/tokens.css`: Halo at
night on bare `:root`, Daylight by day.

**A three-way switch sits in the header — auto / day / night**, added in 0.5.8.
This reverses the original decision that there would be no toggle and nothing
stored; Anthony asked for it, and chose the storage. **`localStorage` is still
barred.** The choice is written to `/data/gnomon-theme.json` by
`POST api/theme`, which is the only write the panel is allowed to make, and is
returned with every `api/projects` payload.

`auto` means *no* `data-theme` attribute, because the attribute is what
switches the media query off. So the day palette is declared **twice** — once
under `@media (prefers-color-scheme: light) { :root:not([data-theme]) }` and
once under `:root[data-theme="day"]` — and a check in the DOM harness asserts
the two copies stay token-for-token identical. Night needs no forced block:
bare `:root` already is night.

Because the stored choice arrives with the first fetch, a forced palette
repaints a beat after load. The device palette shows first.

**`prefers-color-scheme` follows iOS, not Home Assistant's theme setting.** If
HA is pinned dark while the phone is in Light, the light panel renders inside a
dark HA shell.

### Panel constraints, all enforced by checks

- **No `innerHTML`**, no HTML-string concatenation, no `esc()` helper. DOM
  construction only. This was a deliberate decision over keeping escaped
  `innerHTML` — with `textContent` a string cannot become markup, which is
  structural rather than a discipline.
- **Every colour is a token.** No `#rrggbb` or `rgba()` outside `:root` or the
  light media query. Verify with no carve-outs — a check that excludes its own
  failure is not a check.
- No `localStorage` / `sessionStorage`, no external fonts, CDNs, scripts or
  images. The SVG namespace is the only permitted URL. The theme switch does
  not weaken this — its choice lives in `/data`, not in the browser.
- **Relative fetch paths only** — `fetch("api/projects")`. A leading slash
  breaks HA ingress.
- `var()` does not resolve inside SVG presentation attributes. `stroke="var(…)"`
  renders an invisible ring with no error. Ring strokes are set by CSS class.

The footer carries the running version, read from `config.yaml` — which the
Dockerfile now copies into the image so there is still only one place that
declares it. If the footer disagrees with the release you pushed, the container
did not update.

## Deploying

Push to `main`, then in HA: Settings → Add-ons → Add-on Store → ⋮ → **Check for
updates**, hard-reload, then **Update**.

**Update, not Restart** — the panel is baked into the container image.

**The frontend caches separately.** A half-updated board (new ordering, old
tiles) means the browser cached `index.html`. Companion app → Settings →
Companion app → Debugging → **Reset frontend cache**, then force-quit.

## What is on the board right now

12 repos configured, 10 reporting. Ten of them were seeded with headers in one
sitting on 2026-08-17. That reset every `pushed_at` and, until 0.5.3, made all
ten read as freshly worked. With status commits now excluded, the seasonal
projects — Doukas Bus, Pounta, Pilates — drop to `0/wk` and `no code in 30+
days` instead.

`anthonyvenitis.com` is the hero: ships **2026-09-02**, the only targeted
`revenue` project, and decelerating — 2 commits a week against a 25-a-month
average. That deceleration-into-a-deadline is the fact the whole 0.5.0 release
was built to surface.

## Standing rules that bind this repo

- **Never commit, push, or bump a version without explicit permission.** Anthony
  says "commit" / "push" / "yes". Implement, verify, summarise, stop.
- **No attribution of any kind** — no co-author trailers, no generated-by
  notes, nothing describing how the code was produced. Commit messages describe
  the change only. The author is Anthony Venitis.
- **No emoji anywhere** — code, docs, UI, commits. Geometric glyphs only
  (`· ◈ ↑ ↓ ✓ ● ○ —`).
- Never stage `.DS_Store`, `__pycache__`, archives or backups.
- Report what was actually done, including anything repaired beyond the request.

## Next step

See `STATE.md`'s `## Open` section for the live list, and `docs/known-issues.md`
for parked technical findings from both releases.

The momentum-tier `order_reason` fix shipped as **0.5.1**. **0.5.2** followed:

- The deadline branch of `order_reason` now appends the momentum clause, so the
  hero explains both why it ranks first and how fast it is moving. It was the
  only card on the board whose momentum was never spelled out.
- Activity wording is extracted into `_activity_clause`. Unknown momentum
  contributes no clause at all rather than an invented `momentum 0`, and a
  genuine zero falls through to `quiet for N days`.
- New `ranking.why_line` composes the expanded card's footer and drops a
  `debt_reason` that would only restate the rank explanation. Overdue and quiet
  were each being stated twice, at both ends of one line.
- `app.py` sets `card["why"]`; the panel's `detailBlock` reads it instead of
  joining the two fields itself. `debt_reason` is untouched because the rescue
  card still labels itself with it.

That last point makes this a **panel release, not backend-only**. The DOM stub
harness for it is `dom-why.js` in the session scratchpad — it injects an export
before the panel's IIFE closes, then asserts the footer renders `why` verbatim
and that nothing re-appends `debt_reason`. Six checks, all passing.

The strongest remaining candidate is the `--unknown-c` routing in
`docs/known-issues.md` — it reaches `.seg.done` via `--accent`, so an
unknown-state card's progress reads 0% regardless of real progress.
