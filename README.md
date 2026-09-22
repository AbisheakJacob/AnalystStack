# AnalystStack

[![CI](https://github.com/AbisheakJacob/AnalystStack/actions/workflows/workflow.yml/badge.svg)](https://github.com/AbisheakJacob/AnalystStack/actions/workflows/workflow.yml)
[![PyPI](https://img.shields.io/pypi/v/AnalystStack.svg)](https://pypi.org/project/AnalystStack/)
[![Python](https://img.shields.io/pypi/pyversions/AnalystStack.svg)](https://pypi.org/project/AnalystStack/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-zensical-blue.svg)](https://abisheakjacob.github.io/AnalystStack/)

**AnalystStack** is a Python toolkit of reusable helpers for the work data analysts do every
day: connecting to data warehouses, validating and reporting on data quality, reading and
writing files, rendering SQL from templates, and formatting code. It replaces the pile of
copy-pasted snippets every analyst accumulates with a small, tested, `pip install`-able
package.

📖 **Full documentation:** <https://abisheakjacob.github.io/AnalystStack/>

## Installation

```bash
# From PyPI
pip install AnalystStack

# With a warehouse connector -- also available: postgres, databricks, duckdb, snowflake
pip install "AnalystStack[bigquery]"

# With optional validation extras -- scipy-backed drift tests, or a pandera bridge
pip install "AnalystStack[stats,pandera]"

# From GitHub
pip install "git+https://github.com/AbisheakJacob/AnalystStack"
```

## Quickstart

```python
from AnalystStack import io

# Render SQL from an inline Jinja template...
query = io.read.jinja("SELECT * FROM {{ table }} WHERE region = '{{ region }}'",
                      table="sales", region="APAC")

# ...or from a template file on disk.
query = io.read.jinja("queries/monthly_sales.sql.j2", month="2026-05")

# Read an Excel range, write it back out as Markdown.
df = io.read.excel("report.xlsx", sheet_name="Data", start_cell="B2", end_cell="F100")
io.write.markdown(df, "summary.md")
```

```python
from AnalystStack.connectors import GoogleBigQueryConnector

bq = GoogleBigQueryConnector(gcp_project_id="my-project")
df = bq.read_data("SELECT * FROM dataset.table LIMIT 100")
profile = bq.profile_columns("dataset", "table")   # DataFrame: dtype, nullability, fill rate %, ...
```

```python
from AnalystStack import ReportBuilder, Validator, not_null, unique

validation = Validator([not_null("price"), unique("id")]).validate(df)
report = ReportBuilder("Table Data Quality Report").add_validation(validation).build()
report.write("data_quality_report.md")
```

## Modules

### Connectors

Read, write and profile tables in cloud data warehouses — BigQuery, Postgres, Databricks,
Snowflake, and embedded/local DuckDB ([docs](https://abisheakjacob.github.io/AnalystStack/connectors/)).
Every metadata method returns a DataFrame with the same columns across every backend, even
when a given warehouse can't cheaply populate one of them.

| Method | Description |
| ------ | ----------- |
| `read_data(query)` | Run a query and return a DataFrame. |
| `write_data(df, schema, table_id, if_exists="append")` | Write a DataFrame to a table. |
| `list_tables(schema)` | DataFrame of tables, with row count / size / created / last-altered. |
| `list_columns(schema, table_id)` | DataFrame of a table's columns: name, position, dtype, nullability. |
| `profile_columns(schema, table_id)` | `list_columns` plus fill rate / null counts per column. |

### Validation

Attach declarative sanity checks to a DataFrame, without a heavyweight schema library
([docs](https://abisheakjacob.github.io/AnalystStack/validate/)).

| Function / class | Description |
| ----------------- | ----------- |
| `not_null` / `unique` / `in_range` / `is_in` / `matches_regex` / `has_dtype` | Per-column rule factories. |
| `row_count_between` / `no_duplicate_rows` / `is_fresh` / `no_outliers` | Whole-frame / statistical rule factories. |
| `Validator([...]).validate(df)` / `.enforce(df)` | Run every rule; get a report, or raise on failure. |
| `validate.schema.check_schema` / `enforce_schema` | Column existence / order / dtype checks. |
| `validate.drift.compare_dataframe_drift` | Statistical drift between two snapshots of a DataFrame. |
| `validate.referential.check_referential_integrity` | Foreign-key-style checks between two DataFrames. |

### Reporting

Compose validation results, comparisons, and connector metadata into one deliverable — no
scheduling, just a call ([docs](https://abisheakjacob.github.io/AnalystStack/report/)).

```python
from AnalystStack import ReportBuilder

report = ReportBuilder("Orders Data Quality Report").add_validation(validation).build()
report.write("orders_report.xlsx", format="excel")
```

### Tidy data & Compare

`to_tidy` / `from_tidy` reshape DataFrames between wide and long
([docs](https://abisheakjacob.github.io/AnalystStack/tidy/)); `compare_dataframes` /
`summarize` diff two DataFrames and profile one in a single call
([docs](https://abisheakjacob.github.io/AnalystStack/compare/)).

### IO

Read and write data, and render Jinja templates ([docs](https://abisheakjacob.github.io/AnalystStack/io/)).

| Method | Description |
| ------ | ----------- |
| `read.excel` / `read.csv` / `read.parquet` | Read files into DataFrames. |
| `read.jinja(source, **context)` | Render a Jinja template from a **file path or string**. |
| `write.excel` / `write.csv` | Write DataFrames to files. |
| `write.markdown` / `write.txt` | Write a DataFrame or string to Markdown / text. |
| `write.clipboard` | Copy a DataFrame or string to the OS clipboard. |

### Formatting

Format and lint code from Python or the CLI ([docs](https://abisheakjacob.github.io/AnalystStack/formatting/)).

| Class | Description |
| ----- | ----------- |
| `PythonFormatter` | Format and syntax-check Python with Ruff + `ast`. |
| `SQLFormatter` | Format and lint SQL with SQLFluff (any dialect), at a configurable `FormattingLevel` from whitespace-only up to a `sqlglot`-powered structural rewrite. |

```bash
# CLI
analyststack format python path/to/file.py                                    # format in place
analyststack format sql    path/to/query.sql --lint                           # lint only
analyststack format sql    path/to/query.sql --dialect postgres --level low   # light touch-up only
```

## Development

```bash
git clone https://github.com/AbisheakJacob/AnalystStack
cd AnalystStack
pip install -r requirements.txt        # editable install with dev + bigquery extras
```

Common tasks (see the `Makefile`):

| Command | Description |
| ------- | ----------- |
| `make check` | Run format, lint, type-check and tests. |
| `make test` | Run the test suite with coverage. |
| `make format` / `make lint` / `make typecheck` | Individual quality gates. |
| `make build` | Build the sdist and wheel. |
| `make docs` | Build the documentation site. |

The same gates run in CI via [tox](https://tox.wiki/) (`tox -e format,lint,typecheck`,
`tox -e py312,py313`).

## Roadmap

Planned work — and recently closed gaps — live on the
[roadmap](https://abisheakjacob.github.io/AnalystStack/next-steps/).

## License

Released under the [MIT License](LICENSE).
