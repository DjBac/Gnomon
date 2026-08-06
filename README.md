# Venitis Add-ons

Home Assistant add-on repository.

## Installation

Settings → Add-ons → Add-on Store → ⋮ → **Repositories**, then add:

```
https://github.com/DjBac/gnomon
```

## Add-ons

### [Gnomon](./gnomon)

At-a-glance project status board. Reads a four-field header from each of your
GitHub repos' `STATE.md` and renders one line per project in the HA sidebar.
Problems sort to the top; healthy projects sink.

See [the docs](./gnomon/DOCS.md) for configuration and token scope.
