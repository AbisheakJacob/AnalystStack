---
icon: material/map
---

# Roadmap / Next steps

This page tracks where AnalystStack is headed. Items are grouped roughly by priority. It is
intentionally opinionated — the goal is a small, dependable toolkit, not a kitchen sink.

## :material-check-all: Recently done (v0.2.0 — data quality & observability)

A breaking-change release focused on the connectors' and validation's day-to-day ergonomics:

- [x] **Connectors standardized on DataFrames.** `get_all_table_names` / `get_datatypes` /
      `get_fillrate` (returning a `list`/two `dict`s) are replaced by `list_tables` /
      `list_columns` / `profile_columns`, all returning a DataFrame with the same columns
      across every backend — including rich structural metadata (`row_count`, `size_bytes`,
      `created`, `last_altered`) where a warehouse can provide it. This is a breaking change
      (no deprecation shim); see each connector's docstring for exactly which columns it can
      populate.
- [x] **Two new connectors.** `DuckDBConnector` (embedded, zero-configuration — the only
      connector with no required setup) and `SnowflakeConnector` (via
      `snowflake-sqlalchemy`, with the richest metadata of any backend — exact row
      counts/byte sizes/timestamps from a single query).
- [x] **`validate` module significantly expanded**, still without reaching for a
      heavyweight dependency by default:
    - Four new rule factories: `row_count_between`, `no_duplicate_rows`, `is_fresh`,
      `no_outliers`.
    - `validate.schema` — whole-frame structural checks (column existence/order/dtype).
    - `validate.drift` — statistical drift between two snapshots (`population_stability_index`,
      pure pandas/numpy; `ks_test`, requires the `stats` extra).
    - `validate.referential` — referential-integrity checks between two DataFrames.
    - `validate.pandera_bridge` — optional adapter from `pandera`'s failures into this
      package's `ValidationReport` shape, for teams that want pandera's coercion engine
      (requires the `pandera` extra).
- [x] **New `report` module.** `ReportBuilder` composes validation reports, comparison
      results, and connector metadata into a single markdown/Excel/text deliverable, written
      entirely through the existing `io.write` facade — no scheduling, no orchestration.
- [x] **SQL-injection gap closed.** `list_tables`/`list_columns`/`profile_columns` now
      validate their `schema`/`table_id` arguments the same way `write_data` always has.
- [x] **`config.settings` bug fixed.** Settings dataclasses now use
      `field(default_factory=...)` for their environment-variable defaults, so setting an
      env var after import actually takes effect (it silently didn't before).
- [x] **Logging unified.** The Postgres connector's `loguru` usage (the only outlier) is
      replaced with the same stdlib `get_logger` every other module already uses; `loguru`
      is dropped from the `postgres` extra entirely.

Earlier repo-cleanup work (formatting CLI, entry point, connector parity on SQLAlchemy,
`tidy`/`compare`/`validate` modules, docstring-generated docs) is no longer listed here —
see the git history for that pass.

## :material-package-variant: Packaging & dependencies

- [ ] **Single source of truth for metadata.** Consider migrating `setup.cfg` metadata into
      `pyproject.toml` `[project]` to consolidate configuration.
- [ ] **Pin a tested dependency set** for reproducible CI (e.g. a lock file or constraints),
      separate from the loose ranges in `install_requires`.

## :material-test-tube: Testing & quality

- [ ] Add a coverage gate (e.g. `--cov-fail-under=80`) once coverage stabilises.
- [ ] Add tests for `DataReader.excel` / `DataReader.parquet` / `DataWriter.clipboard` — the
      remaining untested `io` paths (the reporting module's Excel path is now covered via
      `test/report/test_report.py`).

## :material-chart-box: Analyst features

- [ ] **Optional Venn diagram** for `compare_dataframes` — a quick visual on top of the
      existing match-rate / overlap numbers.
- [ ] **More warehouse connectors** — Redshift is the next natural candidate, following the
      same Facade + managers pattern as every connector already in the package.
- [ ] **Named, reusable validation suites beyond a plain Python function.** Deliberately not
      built as YAML/JSON in this release — `custom()` rules are arbitrary Python closures,
      and serializing arbitrary code safely isn't possible without an `eval`/`exec`-style
      hole. Revisit only if a genuine cross-language need shows up.

## :material-book-open-variant: Docs & DX

- [ ] Add runnable examples / a short tutorial notebook, including one that builds an
      end-to-end connector → validate → report pipeline.
- [ ] Publish the site to GitHub Pages on every push to `main` (CI is already set up).

---

!!! info "Contributing"

    Picking something up? Open an issue first so we can agree on the shape of the change,
    then send a PR. CI runs formatting, linting, type checks and tests on every push.
