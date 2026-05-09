# Use bash for `trap 'kill 0' EXIT` semantics in `make dev`.
SHELL := /bin/bash

.PHONY: help install dev run assets test lint format typecheck check build docker docker-run clean

# varlock injects schema-validated env vars from .env.schema (+ optional .env.local)
# into the wrapped process. Used for `dev` and `run`; tests/lint/build run raw.
VARLOCK := pnpm exec varlock run --

# Default to public PyPI regardless of any private indexes the contributor's
# machine has configured globally. Override with e.g. `UV_NO_CONFIG=0 make dev`
# if you have a curated mirror you want to use.
#   UV_NO_CONFIG  → uv ignores ~/.config/uv/uv.toml
#   PIP_INDEX_URL → pip subprocesses (e.g. inside pre-commit hook installs)
#                   ignore ~/.config/pip/pip.conf
UV_NO_CONFIG  ?= 1
PIP_INDEX_URL ?= https://pypi.org/simple/

export UV_NO_CONFIG PIP_INDEX_URL

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?##"};{printf "  %-14s %s\n",$$1,$$2}'

install: ## sync python + node deps
	uv sync --all-extras
	pnpm install

assets: ## one-shot build of JS + CSS
	pnpm run assets:build

dev: assets ## run server + asset watchers concurrently with browser auto-reload
	@trap 'kill 0' EXIT; \
	pnpm run assets:watch & \
	$(VARLOCK) env POSTPIT_DEV_RELOAD=1 uv run fastapi dev src/postpit/main.py --port 5176 & \
	wait

run: assets ## run server (no watchers; uses .env.schema + .env.local values)
	$(VARLOCK) uv run python -m postpit

test: ## run pytest
	uv run pytest

lint: ## ruff check + format-check + prettier --check
	uv run ruff check .
	uv run ruff format --check .
	pnpm exec prettier --check .

format: ## ruff format + autofix + prettier --write
	uv run ruff format .
	uv run ruff check --fix .
	pnpm exec prettier --write .

typecheck: ## ty (python) + tsc (typescript)
	uv run ty check
	pnpm run typecheck

check: lint typecheck test ## everything CI runs

build: assets ## build wheel + sdist
	uv build --no-sources

docker: ## build docker image locally
	docker build -t postpit:dev .

docker-run: ## run the locally built image
	docker run --rm -p 5176:5176 postpit:dev

clean: ## wipe build + asset output
	rm -rf dist src/postpit/static/app.js src/postpit/static/app.js.map src/postpit/static/app.css
