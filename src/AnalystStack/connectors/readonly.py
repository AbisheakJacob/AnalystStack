"""Session-level read-only hardening and SQL capture for connectors.

The static check in `AnalystStack.sql_guard` is the first line of defence. Where an engine can
also be told to refuse writes for the whole session, `apply_read_only` does that, so a query
that slips past the parser still cannot change data:

* Postgres: every new connection runs ``SET default_transaction_read_only = on``.
* DuckDB (file databases): the engine is rebuilt with ``read_only=True``.
* ClickHouse: the ``readonly=1`` setting (see `AnalystStack.connectors.clickhouse`).
* BigQuery, Databricks, Snowflake: no session switch is applied here. Use read-only
  credentials for those; this function reports that only the parser guard is in force.

`capture_sql` records the statements a connector actually sends to the database, so catalog
and profiling commands (which build their SQL internally) can still be saved to a task.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event

_NOISE = re.compile(
    r"^\s*(select\s+1\s*;?\s*$|set\s|show\s|begin|commit|rollback|select\s+pg_catalog\.version|"
    r"select\s+current_schema|select\s+current_database|pragma\s|select\s+version\(\))",
    re.IGNORECASE,
)
# pandas.read_sql first asks the dialect whether its argument is a table name; that probe is dialect SQL the analyst
# never wrote, so it is not saved. Signatures seen so far: DuckDB (duckdb_tables UNION ALL BY NAME duckdb_views) and
# Postgres (pg_table_is_visible).
_PROBE = re.compile(r"union\s+all\s+by\s+name|pg_table_is_visible", re.IGNORECASE)


def engine_of(connector):
    """Returns the SQLAlchemy engine behind a connector.

    Raises:
        AttributeError: If the connector exposes no engine.
    """
    return connector._client_wrapper.engine


def apply_read_only(connector, db_type: str) -> str:
    """Puts the connector's session into read-only mode where the engine supports it.

    Args:
        connector: A connected connector instance.
        db_type: The connection type, such as ``"postgres"``.

    Returns:
        A short sentence stating what is in force, for display. Never contains credentials.
    """
    engine = engine_of(connector)
    if db_type == "postgres":

        @event.listens_for(engine, "connect")
        def _read_only(dbapi_connection, _record):  # pragma: no cover - needs a live server
            cursor = dbapi_connection.cursor()
            cursor.execute("SET default_transaction_read_only = on")
            cursor.close()
            dbapi_connection.commit()

        engine.dispose()  # drop pooled connections opened before the hook existed
        return "postgres session set to read only"
    if db_type == "duckdb":
        wrapper = connector._client_wrapper
        path = getattr(wrapper, "database_path", ":memory:")
        if path == ":memory:":
            return "duckdb in-memory database: parser guard only"
        engine.dispose()
        wrapper._engine = create_engine(f"duckdb:///{path}", connect_args={"read_only": True})
        return "duckdb opened read only"
    if db_type == "clickhouse":
        return "clickhouse readonly=1 applied at connect time"
    return f"{db_type}: parser guard only (use read-only credentials)"


@contextmanager
def capture_sql(connector) -> Iterator[list[str]]:
    """Collects the SQL statements a connector sends while the context is open.

    Args:
        connector: A connector instance.

    Yields:
        A list that fills with statements in execution order, with engine housekeeping such as
        ``SELECT 1`` and ``SET ...`` filtered out. Bound parameter values are not included.
    """
    engine = engine_of(connector)
    statements: list[str] = []

    def _before(_conn, _cursor, statement, _parameters, _context, _executemany):
        if not _NOISE.match(statement) and not _PROBE.search(statement):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", _before)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", _before)
