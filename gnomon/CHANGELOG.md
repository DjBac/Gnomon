# Changelog

## 0.1.0

Initial release.

- Polls GitHub for `STATE.md` in each configured repo
- Parses a four-field front-matter header: `project`, `next`, `blocker`, `updated`
- Ingress panel, sorted problems-first (blocked → stale → aging → fresh)
- Configurable poll interval and stale threshold
- Read-only; write-back deferred to v2
