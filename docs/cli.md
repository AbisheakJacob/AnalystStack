---
icon: material/console
---

# Command line

The `analyststack` command exposes the package from the shell. Every command group is a thin
layer over the Python API, so anything you can do here you can also do in code.

```bash
analyststack --help
analyststack db --help
```

Exit codes: `0` success, `1` an expected failure (bad input, a failed check), `2` blocked by the
path policy or the read-only SQL guard.

## Commands

| Command | What it does |
|---|---|
| `format sql\|python FILE [--lint]` | Lint or format a file (see [Formatting](formatting.md)). |
| `env check [--path P] [--strict]` | Compare each level's `.env` with `.env.example`. Prints key **names** only. |
| `db connections` | List the connection names defined in `config.yaml` (no secrets). |
| `db check-sql (--sql S or --file F) --dialect D` | Run only the read-only guard; no connection is made. |
| `db query --connection C (--sql S or --file F) --title T --description D` | Run one guarded, saved, row-capped read. Options: `--limit N`, `--no-limit`, `--out FILE`. |
| `db tables --connection C --schema S` | List base tables. |
| `db columns --connection C --schema S --table T` | List a table's columns. |
| `db profile --connection C --schema S --table T` | Per-column fill rate. |
| `db freshness --connection C --table S.T [--column COL] [--max-age-hours N]` | Age of the newest value; exits `1` when stale. Default column `syncstartdatetime`. |
| `io render (--file F or --text T) [--var NAME=VALUE] [--out F]` | Render a Jinja template. |
| `io convert IN OUT` | Convert between `.csv`, `.xlsx`, `.parquet`; write `.md` or `.txt`. |
| `io head FILE` | Shape and first rows. |
| `data tidy IN OUT --id-vars A,B` / `data untidy IN OUT --index A --columns C --values V` | Reshape wide to tidy and back. |
| `data compare LEFT RIGHT --on KEY [--out F]` | Compare two files on a key; exits `1` if they differ. |
| `data summarize FILE` | One-call profile. |
| `data validate FILE --rules RULES.yaml` | Declarative checks; exits `1` on failure. |
| `report build --title T --section NAME=FILE --out F` | Markdown, text or Excel report. |
| `excel build --title T --data FILE --out F.xlsx` | Branded workbook: Summary, Data, Notes, Query provenance. |

There is no command that writes to a database, and none that prints a credential.

## Read-only database access

Connections are referred to by name. A connection is declared in `config.yaml` with the
*names* of the environment variables that hold its settings:

```yaml
connections:
  warehouse_pg:
    type: postgres          # postgres | bigquery | databricks | snowflake | duckdb | clickhouse
    env:                    # connector argument -> variable NAME
      host: WAREHOUSE_PG_HOST
      user: WAREHOUSE_PG_USER
      password: WAREHOUSE_PG_PASSWORD
    options:                # non-secret literals
      database: analytics
    read_only: true         # the only supported value
```

Values come from the `.env` files at each level (see [Workspace layout](#workspace-layout)),
are held in memory only, and are never printed or logged. Connector logging is silenced in
the CLI for the same reason, and connection errors are reported without driver text. Set
`ANALYSTSTACK_DEBUG=1` to see both when debugging locally.

Protection layers, in the order they apply:

1. **Parser guard.** `AnalystStack.sql_guard.assert_read_only` accepts exactly one query
   statement and walks the whole syntax tree. It refuses DML, DDL, transaction and session
   statements, `SELECT ... INTO`, `FOR UPDATE`, unparsed commands and file or network
   functions (for example ClickHouse `url`/`file`/`s3`/`remote`, Postgres `pg_read_file`/
   `dblink`/`lo_*`), including inside CTEs such as `WITH x AS (DELETE ... RETURNING *)`.
2. **Session read-only.** Postgres connections run `SET default_transaction_read_only = on`,
   DuckDB files open read only, ClickHouse connects with `readonly=1`.
3. **Credentials.** BigQuery, Databricks and Snowflake have no session switch here, so only the
   parser guard is in force. Use read-only credentials for those.

### Every statement is saved

`db query` saves the statement to `<task>/sql/NN_slug.sql` before running it:

```sql
/*
Author: <author>
Date: YYYY/MM/DD
Title: <title>
Description: <description>
*/
SELECT ...;
```

The author comes from `author:` in `global/config.yaml`. Run details (connection name, row
count, time, outcome) go to `sql/_runs.jsonl`, not the header. An identical statement reuses
its file. `tables`, `columns`, `profile` and `freshness` save the SQL they ran with an
auto-generated title and description. A refused statement is never saved. With no active task
and no `--task-dir`, a command refuses to run; `--scratch` saves to `_state/inbox/sql/`.

## Path policy

Every file the CLI reads or writes first goes through `AnalystStack.paths`:

- no file named like an environment file (`.env`, `.env.local`, `prod.env`) can be read or
  written; only `.env.example` can be read;
- inside a workspace, reads and writes must stay inside it;
- writes are limited to `_state/`, `global/` and `clients/`, never into `refs/`, `.claude/`,
  `scripts/`, `templates/` or `.git/`, and a path inside a `tasks/NNNN_*` folder must belong
  to the active task.

Outside a workspace only the environment-file rule applies. This is a guardrail for the CLI.
Code that imports the package directly is not subject to it.

## Workspace layout

The package finds a workspace by walking up from the current directory (or from the target
path) to the first folder containing `global/config.yaml`. The active task is the folder named
in `_state/active_task`, relative to that root. No environment variable is used, because a
hook or child process cannot change the environment of later commands. Environment files
exist at three levels only and are loaded global first, then client, then product, so a child
overrides its parent (`AnalystStack.config.env_cascade.load_env_cascade`):

```text
global/.env
clients/<client>/.env
clients/<client>/products/<product>/.env
```

## Python API

```python
from AnalystStack.config.env_cascade import load_env_cascade, check_env
from AnalystStack.connections import open_connection
from AnalystStack.sql_guard import assert_read_only
from AnalystStack.sqllog import save_query, read_provenance
from AnalystStack.connectors.freshness import check_freshness
from AnalystStack.report.excel import build_branded_workbook, Theme
```

::: AnalystStack.cli

::: AnalystStack.sql_guard

::: AnalystStack.paths

::: AnalystStack.sqllog
