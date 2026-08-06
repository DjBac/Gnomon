# Changelog

## 0.2.0

**Breaking header change.** The `STATE.md` front-matter schema is not backward
compatible. Existing headers keep rendering, but `updated` is ignored and the
three new fields fall back to their defaults until you backfill them.

- Schema goes from four fields to six: `project`, `phase`, `stakes`, `target`,
  `next`, `blocker`
- `updated` removed from the header — freshness is now derived from the repo's
  `pushed_at` timestamp, so it can no longer drift out of date
- `priority` is computed from `stakes`, `target`, `blocker` and `phase` rather
  than stored, and is exposed as both a `score` and a `high`/`normal`/`low` band
- Sort is now priority-descending with age as a tiebreak, replacing the old
  problems-first order — blocked work gets a 1.4× multiplier and surfaces on
  its own merits
- New `parked` card state for projects deliberately set down
- Each repo now costs two GitHub calls per cycle: metadata plus `STATE.md`
- Distinct notes for 401, 403 and 404 on the metadata call, so a bad token
  reads differently from a misspelled repo name
- Options are re-read on every poll cycle — changing configuration no longer
  requires restarting the add-on
- `api/projects` gains `phase`, `stakes`, `target`, `days_to_target`,
  `priority` and `score` per card, plus a `phases` list on the response

## 0.1.0

Initial release.

- Polls GitHub for `STATE.md` in each configured repo
- Parses a four-field front-matter header: `project`, `next`, `blocker`, `updated`
- Ingress panel, sorted problems-first (blocked → stale → aging → fresh)
- Configurable poll interval and stale threshold
- Read-only; write-back deferred to v2
