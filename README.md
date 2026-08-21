# Venitis Add-ons

Home Assistant add-on repository.

## Installation

Settings → Add-ons → Add-on Store → ⋮ → **Repositories**, then add:

```
https://github.com/DjBac/Gnomon
```

## Add-ons

### [Gnomon](./gnomon)

At-a-glance project status board. Reads a six-field header — including a
`steps` list — from each of your GitHub repos' `STATE.md` and renders one
line per project in the HA sidebar. Cards are ordered by imminent deadline
first, then by momentum from recent commit activity.

See [the docs](./gnomon/DOCS.md) for configuration and token scope.
