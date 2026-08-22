# Known issues

Findings raised during code review across 0.4.0 and 0.5.0 and deliberately not
fixed at the time. Each was judged real and non-blocking. Recorded here so a
future reviewer does not rediscover them as new, and so a mechanical audit does
not "fix" something that was a considered choice.

Ordered roughly by how much they matter.

## Display

**`--unknown-c` reaches data-bearing surfaces.**
It is routed through `--accent`, so besides the accent rail it also paints
`.seg.done`, `.actbar i`, `.badge` (text and border), `.nowline`, `.verdict`
and `.steps li.current .mark`. Done-segments against their track measure 1.40:1 in day and 1.30:1 at
night, so an unknown-state card's progress row reads as 0% regardless of actual
progress. Reachable when a repo has a `STATE.md` but no pushes.
The alpha itself is correct — raising it to make segments legible collapses the
stale-versus-unknown distinction it exists to create. **The fix is to stop
routing `--unknown-c` through `--accent` for the data-bearing consumers**, not to
change the tone.

**A tail row without an activity bar aligns differently from one with.**
`.actbar { flex: 1 }` consumes free space before auto margins resolve, so
`.count` lands mid-row on bar-less rows and at the right edge on bar rows. The
`margin-left: auto` on `.card.tail .age` was removed for this reason; the
residual is the ordered outcome and arguably the honest reading — no bar, no
column.

**Daylight hover is inverted.**
`--dim-state` is `.82` in day while `:hover` remains `.8`, so hovering a stale
or parked card by day makes it 0.02 dimmer instead of lifting it. Imperceptible,
and leaving `:hover` alone was explicit.

**Config values are not validated against anything.** `panel_icon: mdi:sundial`
shipped for months and rendered a blank sidebar icon, because MDI has no
`sundial` and Home Assistant draws nothing rather than falling back. No test
could have caught it — the suite never reads `config.yaml`, and validating icon
names would mean shipping a copy of the MDI index. Worth knowing that this file
has no coverage at all.

## Contrast

Measured, not eyeballed. None are regressions — the Argus adoption improved the
tertiary tier from 2.90:1 to 3.13:1 at night.

- **Pace arrows are sub-AA at 11.5px, in opposite palettes.** Night `↓` 3.67:1,
  day `↑` 3.49:1. Token-tier and inherited; changing `--ok` / `--crit` would
  desync from Argus, which the spec approved adopting verbatim.
- **The whole `--text-3` tier is sub-AA** — 3.13:1 night, 3.87:1 day, used at
  9.5–13px for `.age`, `.count`, `.meta`, `.why`, `.note`, `.stakekey`.
- **On dimmed day cards neither text tier clears AA** — `--text-2` reaches
  4.20:1 and `--text-3` 2.91:1 at `--dim-state: .82`. An improvement over `.55`
  (2.44:1 and 1.96:1, effectively invisible), not a resolution.
- **Activity bar fill against its track is 2.87:1 in day** for the `fresh`
  state, which is currently every reporting repo. A 4% shortfall on saturated
  green against near-white.

## Backend

**A STATE.md fetch failure overwrites the vanished-field snapshot.**
When `fetch_state_md` fails or front-matter will not parse, `meta` stays `{}`
and `watched_values({})` returns all-empty. No false "removed" note fires,
because `card["note"]` is already occupied on every such path — but a genuine
field removal happening inside an outage window is never reported. Safe by
consequence rather than by design.

**A present-but-unrecognised value reads as vanished.**
`phase: wip` or `target: soon` normalises to `""`, so the vanished-field check
reports it removed — every poll, permanently, for a line sitting in the file.
The signal is arguably useful; the wording is wrong for that case. Roughly ten
lines in `state.watched_values` / `vanished` to distinguish "key absent" from
"value unrecognised".

**An unparseable `target` is dropped silently.**
`the-bridge` carries `target: "Poseidonia 2028"`, which is discarded with no
note — while a *removed* target does produce one. Inconsistent with this
project's own stance on silent field loss.

**The repo-name tiebreak is case-sensitive ASCII**, so `DjBac/Gnomon` sorts
ahead of lowercase repos on a full tier/momentum/stakes tie.

**`premiere`'s `STATE.md` is 409 KB**, of which the header is 14 lines, and it is
refetched in full every poll — roughly 38 MB/day. The DOCS rate-limit section
counts requests, not bytes.

**Four GitHub calls per repo per cycle.** 12 repos every 15 minutes is ~192
calls/hour against a 5,000/hour limit. The fourth is the `path=STATE.md`
commits call that tells bookkeeping apart from work.

## Not defects — recorded so they are not "fixed"

**`--unknown-c` is deliberately low-contrast** (~1.7:1). It reads as *absent*
rather than quiet, which is the point. A mechanical contrast audit will flag it.

**`--stale-c` and `--text-3` are intentionally identical** (`#6d7684` night,
`#7a8290` day) — both are Argus values. `unknown` was given its own token
instead of changing either.

**`.card` and `button.refresh` hardcode `backdrop-filter` instead of using
`--blur`.** Zero visual impact — day surfaces are opaque — but it forces GPU
compositing on 12 cards in a phone webview for no gain.
