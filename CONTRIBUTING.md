# Contributing

Thanks for your interest in postpit. This is an early-stage project; expect rough edges.

## Supported platforms

postpit's CI matrix covers Linux and macOS on Python 3.12, 3.13, and 3.14.
Windows is not actively tested; patches that keep it working are welcome but
not required.

## Local setup

You need:

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) ≥ 0.11
- Node 22 + pnpm 11 (via `corepack enable`)

```bash
git clone https://github.com/socialpyre/postpit
cd postpit
make install            # uv sync + pnpm install
uv run pre-commit install
```

### Configuration

postpit's env-var contract is schema-driven via [varlock](https://varlock.dev).
The committed `.env.schema` declares every supported variable with its type and
validation rules. To override defaults locally, create a gitignored `.env.local`:

```bash
cp .env.schema .env.local
# edit values, drop the `# @` decorator lines
```

`make dev` and `make run` execute under `pnpm exec varlock run --`, which
parses the schema, layers in any `.env.local` overrides, validates, then
injects the resolved values into the subprocess. Plain `pytest` and other
`uv run` calls bypass varlock and just use the application's pydantic-settings
defaults.

To debug what varlock would inject, run `pnpm exec varlock load`.

### If you have a private package index configured globally

If your machine has a private Python index (AWS CodeArtifact, JFrog, GitHub
Packages, Azure Artifacts, etc.) configured via `~/.config/uv/uv.toml`,
`~/.config/pip/pip.conf`, or environment variables, export these in your shell
before working on postpit so that `uv`, `pip`, and pre-commit all resolve from
public PyPI:

```bash
export UV_NO_CONFIG=1
export PIP_INDEX_URL=https://pypi.org/simple/
```

The `Makefile` already sets these for `make` targets, but pre-commit runs
through your shell on `git commit`, so the shell-level export is what matters
there. The `no-private-index` pre-commit hook is the safety net that prevents
private-index URLs from accidentally landing in committed files.

## Common tasks

| Command          | What it does                                                                     |
| ---------------- | -------------------------------------------------------------------------------- |
| `make dev`       | Run the FastAPI dev server + JS/CSS watchers + browser auto-reload (via varlock) |
| `make run`       | Run the server only, no watchers (via varlock)                                   |
| `make assets`    | One-shot rebuild of `src/postpit/static/{app.js,app.css}`                        |
| `make test`      | Run pytest                                                                       |
| `make lint`      | `ruff check` + `ruff format --check`                                             |
| `make typecheck` | `ty check` (Python) + `tsc --noEmit` (TypeScript)                                |
| `make check`     | Everything CI runs (lint + typecheck + test)                                     |
| `make build`     | Build wheel + sdist                                                              |
| `make docker`    | Build the Docker image locally                                                   |

Run `make check` before pushing — it mirrors what CI will run.

## Live reload

`make dev` starts three watchers under one shell:

- `fastapi dev` (uvicorn `--reload`) restarts the server on `.py` / `.toml` edits.
- `esbuild --watch` rebuilds `src/postpit/static/app.js` on `.ts` edits.
- `tailwindcss --watch` rebuilds `src/postpit/static/app.css` on template / CSS edits.
- [`arel`](https://pypi.org/project/arel/) is mounted as a dev-only WebSocket route at
  `/hot-reload`. The base template injects a `<script>` (gated by `POSTPIT_DEV_RELOAD=1`)
  that listens to that socket and reloads the browser when watched files change.

A single Ctrl-C kills all four; the `Makefile` uses `trap 'kill 0' EXIT`.

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/) so
[python-semantic-release](https://python-semantic-release.readthedocs.io/) can derive
versions and changelogs:

| Prefix                                                                        | Effect             |
| ----------------------------------------------------------------------------- | ------------------ |
| `feat: ...`                                                                   | Minor version bump |
| `fix: ...`, `perf: ...`                                                       | Patch version bump |
| `docs:`, `chore:`, `ci:`, `test:`, `refactor:`, `build:`, `style:`, `revert:` | No release         |
| `feat!: ...` or `BREAKING CHANGE:` in footer                                  | Major version bump |

The `conventional-pre-commit` hook will block non-conforming messages.

## Releasing

Maintainers only. Pushing conventional commits to `main` triggers `release.yml`,
which creates the tag and GitHub Release; that fires `publish.yml` which uploads
the wheel and sdist to PyPI via
[trusted publishing](https://docs.pypi.org/trusted-publishers/), and `docker.yml`
which builds and pushes the multi-arch image to GHCR.

## Keeping pinned tooling fresh

A few things aren't covered by Dependabot — bump them manually on a
roughly-monthly cadence:

- **Pre-commit hooks** — run `uv run pre-commit autoupdate` and commit the
  rev bumps as `chore: bump pre-commit hooks`.
- **uv binary in `Dockerfile`** — Dependabot's `docker` ecosystem only
  tracks top-level `FROM` images, not `COPY --from=ghcr.io/astral-sh/uv:X.Y.Z`.
  Watch <https://github.com/astral-sh/uv/releases> and bump the tag in the
  Dockerfile alongside `[tool.uv].required-version` in `pyproject.toml`.

## Reporting issues

- Bugs / feature requests: open a GitHub Issue.
- Security vulnerabilities: see [SECURITY.md](./SECURITY.md) — please do **not** open a public issue.

## Code of Conduct

By participating you agree to follow our [Code of Conduct](./CODE_OF_CONDUCT.md).
