"""Read-only SQL guard.

`assert_read_only` accepts a SQL string only if it is exactly one statement that is a plain
query and contains nothing that can change data, schema, session state or the outside world.
It parses with the target engine's dialect and walks the *whole* syntax tree, not just the
root node, so constructs such as a Postgres writable CTE
(``WITH x AS (DELETE ... RETURNING *) SELECT ...``) are refused.

Refused: more than one statement; anything that is not a query at the root; DML, DDL and
transaction or session statements anywhere in the tree; ``SELECT ... INTO``; row locks
(``FOR UPDATE``); unparsed commands (``CALL``, ``EXEC``, ``VACUUM``...); and calls to
functions that read files, reach other servers or have side effects (for example ClickHouse
``url``/``file``/``s3``/``remote`` and Postgres ``pg_read_file``/``dblink``/``lo_*``).
Any parse error is a refusal.

This is a static check. It complements, and never replaces, read-only database credentials
and the session-level read-only settings that the connectors apply where the engine has them.
"""

import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from AnalystStack.exceptions.errors import ReadOnlyViolationError

_FORBIDDEN_NODE_NAMES = (
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "TruncateTable", "Grant",
    "Revoke", "Command", "Copy", "Use", "Set", "Into", "Lock", "LoadData", "Analyze", "Pragma",
    "Attach", "Detach", "Transaction", "Commit", "Rollback", "Comment", "Kill", "Declare",
    "Export", "Refresh", "Cache", "Uncache", "Execute", "Install", "Describe", "Show",
)  # fmt: skip
_FORBIDDEN_NODES = tuple(getattr(exp, name) for name in _FORBIDDEN_NODE_NAMES if hasattr(exp, name))

_FORBIDDEN_FUNCTIONS = frozenset(
    {
        # ClickHouse table functions that read files or reach other systems
        "url", "urlcluster", "file", "filecluster", "s3", "s3cluster", "gcs", "azureblobstorage",
        "hdfs", "hdfscluster", "remote", "remotesecure", "cluster", "clusterallreplicas",
        "mysql", "postgresql", "mongodb", "redis", "jdbc", "odbc", "executable", "input", "sqlite",
        # Postgres file access, cross-database calls, large objects, session and lock side effects
        "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file", "pg_ls_logdir",
        "dblink", "dblink_exec", "dblink_connect", "dblink_send_query", "set_config", "nextval",
        "setval", "pg_sleep", "pg_terminate_backend", "pg_cancel_backend", "pg_reload_conf",
        "pg_advisory_lock", "pg_advisory_xact_lock", "pg_try_advisory_lock", "copy_to",
        # DuckDB readers and exporters
        "read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto", "read_text",
        "read_blob", "glob", "readcsv", "read_ndjson", "parquet_scan", "csv_scan", "sniff_csv",
        # Databricks and Snowflake file readers
        "read_files", "read_kafka", "list_files", "copy_into",
    }
)  # fmt: skip
_FORBIDDEN_FUNCTION_PREFIXES = ("lo_", "dblink", "pg_read", "pg_ls", "pg_file")

DIALECT_BY_TYPE = {
    "bigquery": "bigquery",
    "postgres": "postgres",
    "databricks": "databricks",
    "duckdb": "duckdb",
    "snowflake": "snowflake",
    "clickhouse": "clickhouse",
}


def _function_name(node: object) -> str | None:
    if isinstance(node, exp.Anonymous):
        return str(node.name).lower()
    if isinstance(node, exp.Func):
        return str(node.key).lower()
    return None


# sqlglot names typed functions without underscores (``readparquet``), so compare with underscores removed too.
_FORBIDDEN_FUNCTIONS_FLAT = frozenset(name.replace("_", "") for name in _FORBIDDEN_FUNCTIONS)
# A quoted table name that is really a file path or URL, which DuckDB reads in place: FROM 'data.csv'.
_FILE_REFERENCE = re.compile(
    r"[/\\]|://|\.(?:csv|tsv|parquet|json|jsonl|ndjson|txt|gz|zst|xlsx|xls|db|sqlite|duckdb)$",
    re.IGNORECASE,
)


def _forbidden_function(name: str) -> bool:
    return (
        name in _FORBIDDEN_FUNCTIONS
        or name.replace("_", "") in _FORBIDDEN_FUNCTIONS_FLAT
        or name.startswith(_FORBIDDEN_FUNCTION_PREFIXES)
    )


def assert_read_only(sql: str, dialect: str | None = None) -> exp.Query:
    """Checks that ``sql`` is a single read-only query and returns its parsed tree.

    Args:
        sql: The SQL text to check.
        dialect: A sqlglot dialect name such as ``"postgres"`` or ``"clickhouse"``. Parsing
            with the wrong dialect can change what is seen, so always pass the dialect of
            the connection the query will run against.

    Returns:
        The parsed syntax tree of the single statement.

    Raises:
        AnalystStack.exceptions.errors.ReadOnlyViolationError: If the SQL is empty, cannot be
            parsed, is not exactly one statement, or contains anything that is not a plain
            read. The message names the reason but never echoes the SQL text.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise ReadOnlyViolationError("Empty SQL is not allowed.")
    if "\x00" in sql:
        raise ReadOnlyViolationError("SQL contains a NUL byte.")
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except SqlglotError as exc:
        raise ReadOnlyViolationError(f"SQL could not be parsed with dialect {dialect!r}; refusing it.") from exc
    except Exception as exc:  # noqa: BLE001 - any parser failure must fail closed
        raise ReadOnlyViolationError("SQL could not be parsed; refusing it.") from exc

    if len(statements) != 1:
        raise ReadOnlyViolationError(f"Exactly one statement is allowed, found {len(statements)}.")
    root = statements[0]
    if not isinstance(root, exp.Query):
        raise ReadOnlyViolationError(f"Only SELECT queries are allowed, found {type(root).__name__}.")

    for node in root.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            raise ReadOnlyViolationError(f"Forbidden construct in query: {type(node).__name__}.")
        name = _function_name(node)
        if name is not None and _forbidden_function(name):
            raise ReadOnlyViolationError(f"Forbidden function in query: {name}.")
        if isinstance(node, exp.Func) and type(node).__name__.startswith("Read"):
            raise ReadOnlyViolationError(f"Forbidden file reader in query: {type(node).__name__}.")
        if isinstance(node, exp.Table) and _FILE_REFERENCE.search(str(node.name)):
            raise ReadOnlyViolationError("A file path or URL used as a table name is not allowed.")
        if isinstance(node, exp.Table) and isinstance(node.this, exp.Expression):
            inner = None if isinstance(node.this, exp.Identifier) else _function_name(node.this)
            if inner is not None and _forbidden_function(inner):
                raise ReadOnlyViolationError(f"Forbidden table function in query: {inner}.")
    return root
