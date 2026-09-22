"""Cloud data-warehouse connectors: read, write, and profile tables through a uniform interface.

Every connector implements the `BaseConnector` contract (`read_data`, `write_data`,
`list_tables`, `list_columns`, `profile_columns`) and reads/writes through a SQLAlchemy
``Engine``, so the same code works against any backend below by swapping the connector
class. `list_tables`/`list_columns`/`profile_columns` always return a DataFrame with the
same columns across every backend, even when a given warehouse can't cheaply populate one
of them (see each connector's own docstring for exactly which columns that applies to).

Exports:
    - `BaseConnector`: The abstract base class every connector implements.
    - `GoogleBigQueryConnector`: Connector for Google BigQuery, via ``sqlalchemy-bigquery``.
    - `PostgresConnector`: Connector for PostgreSQL, via ``psycopg2``.
    - `DatabricksConnector`: Connector for Databricks SQL warehouses, via
        ``databricks-sqlalchemy``.
    - `DuckDBConnector`: Connector for embedded/local DuckDB, via ``duckdb-engine``. The only
        connector requiring zero configuration.
    - `SnowflakeConnector`: Connector for Snowflake, via ``snowflake-sqlalchemy``.

Example:
    ```python
    from AnalystStack.connectors import GoogleBigQueryConnector

    bq = GoogleBigQueryConnector(gcp_project_id="my-gcp-project", gbq_project_id="my-gbq-project")
    df = bq.read_data("SELECT * FROM analytics.orders LIMIT 1000")
    bq.write_data(df, schema="analytics", table_id="orders_copy", if_exists="replace")
    ```
"""

from .base import BaseConnector
from .bigquery import GoogleBigQueryConnector
from .databricks import DatabricksConnector
from .duckdb import DuckDBConnector
from .postgres import PostgresConnector
from .snowflake import SnowflakeConnector

__all__ = [
    "BaseConnector",
    "DatabricksConnector",
    "DuckDBConnector",
    "GoogleBigQueryConnector",
    "PostgresConnector",
    "SnowflakeConnector",
]
