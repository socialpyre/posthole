# Templates

Jinja templates rendered through `fastapi-hotwire` (`HotwireTemplates` =
Starlette `Jinja2Templates` + a flash context processor + Turbo block helpers).
Loader and entrypoint live in `src/posthole/web/templates.py`.

## Layout

| Directory     | Role                                                              |
| ------------- | ----------------------------------------------------------------- |
| `layouts/`    | Root skeletons. Pages `{% extends %}` from here.                  |
| `partials/`   | Static fragments included via `{% include %}` (sidebar, navbar).  |
| `components/` | `{% macro %}` libraries imported by pages (buttons, form fields). |
| `pages/`      | Full-document templates, grouped by domain (`home/`, platform).   |
| `frames/`     | Turbo Frame fragments — single `<turbo-frame id="…">` root.       |
| `streams/`    | Turbo Stream responses — one or more `<turbo-stream>` elements.   |
| `errors/`     | 404, 500, and friends.                                            |

Empty subdirectories carry a `.gitkeep` so the shape is committed before the
first page lands in them.

## Conventions

**Extension.** Always `.html.j2`. Editors get HTML highlighting from `.html`
and Jinja support from `.j2`.

**Autoescape.** Always on. Starlette's `Jinja2Templates` and Hotwire's
constructor both enforce this — never disable it. Block output is
interpolated into Turbo Stream markup verbatim, so disabling autoescape would
turn any user-supplied variable into an XSS sink.

**Block contract.** `layouts/app.html.j2` exposes:

- `{% block page_title %}` — `<title>` content. Defaults to `posthole`.
- `{% block main %}` — primary content slot, rendered inside the layout's
  `<main class="flex-1 min-w-0">`.

New layouts must declare their block contract in a leading comment so callers
know what they can override.

**Frames.** A frame template renders exactly one `<turbo-frame id="…">`
element as its root. Use `templates.TemplateResponse(...)` and let the page
contain a matching `<turbo-frame>` for the swap.

**Streams.** A stream template renders one or more
`<turbo-stream action="…" target="…">` elements. Use the fastapi-hotwire
`TurboStream` response helper rather than building the markup by hand.

**Naming.** Directory placement is the namespace —
`partials/sidebar.html.j2`, not `_sidebar.html.j2`. Don't carry the
underscore-prefix convention from other ecosystems.

## Adding custom filters and globals

Edit `src/posthole/web/templates.py`. After `HotwireTemplates(...)` is
constructed, attach to `templates.env.filters[...]` and
`templates.env.globals[...]`. That function is the single home for
template-environment configuration.
