# Schema migrations

Posthole stores state in a single SQLite file (or `:memory:` for ephemeral
runs). Schema changes ship as ordered, append-only SQL migrations.

## End-user upgrade guide

### Auto-migrate on startup

`posthole` applies any pending migrations as part of its lifespan startup.
A standard `docker compose pull && docker compose up -d` is enough to bring
your schema current — no extra commands.

```
docker compose pull
docker compose up -d
docker compose logs posthole | grep "applied migration"
```

You'll see one `applied migration version=N` log line per migration that ran.

### Back up before bumping

Migrations are forward-only. If a migration fails or you want to roll back,
the only path is to restore your database file. Before every version bump:

```
cp ./data/posthole.db ./data/posthole.db.backup-$(date +%F)
```

(Adjust the path to wherever you point `POSTHOLE_DATABASE_URL`.)

### Downgrade is unsupported

If you point an older `posthole` image at a database written by a newer
build, startup will fail with a clear error:

```
Database is at schema version 5 but this posthole build only knows up to
version 2. You likely downgraded — pin a newer image or restore from backup.
```

This is intentional: silently running with a too-old binary would corrupt
data the moment a query referenced a column or table the binary doesn't
know about. Restore the backup that was current with that older build.

### Optional: previewing before bumping

If you want to see what would be applied before letting the server boot:

```
docker run --rm \
  -v ./data:/data \
  -e POSTHOLE_DATABASE_URL=/data/posthole.db \
  ghcr.io/socialpyre/posthole:NEW_VERSION \
  posthole migrate --dry-run
```

Prints the pending migrations and exits without writing anything.

## Maintainer (developer) workflow

### Adding a migration

1. Add a SQL file to `src/posthole/db/migrations/` named
   `NNNN_short_description.sql`, where `NNNN` is the next zero-padded
   version number. The loader (`src/posthole/db/migrations/loader.py`)
   discovers files lexicographically and the filename's numeric prefix
   _is_ the on-disk schema version. Don't reorder or renumber existing
   files.
2. Prefer additive changes — `ADD COLUMN ... NULL`, `CREATE TABLE`,
   `CREATE INDEX`. Avoid `DROP COLUMN` / type changes until we have a
   pre-destructive backup hook.
3. Each file is run via `executescript`, so multi-statement migrations
   are fine (semicolon-separated SQL).
4. Ship in a normal patch/minor release.

### Rules of the road

- **Immutable after release.** Once a migration ships in a tagged version,
  never edit it. Add a new migration that fixes whatever was wrong.
- **Append-only.** Never reorder or insert a migration in the middle of
  the directory. The numeric filename prefix is the on-disk schema version.
- **Pre-1.0 exception.** Until v1.0 we reserve the right to reset
  migration 0 between minor versions if the schema needs to change shape.
  Any such break MUST be called out in `CHANGELOG.md` with a
  "wipe `POSTHOLE_DATABASE_URL` before upgrading" note. After v1.0, this
  escape hatch closes.

### CLI

The same binary serves both the web app and the migrate command:

```
posthole                  # launch the server
posthole migrate          # apply pending migrations, exit
posthole migrate --dry-run  # list pending migrations, exit
```

`POSTHOLE_DATABASE_URL` selects the target DB in all three modes.

### Testing migrations

The `db` fixture in `tests/conftest.py` opens a fresh `:memory:` Database
per test, so every test runs against a fully-migrated empty schema.

For idempotency tests (does re-opening apply migrations twice?), use the
`tmp_path` pytest fixture to get a real file path —
`tests/db/test_db.py::test_migrations_idempotent_across_reopen` is the
template.
