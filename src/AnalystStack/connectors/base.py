"""Shared contract for every warehouse connector in this package.

Every connector (`AnalystStack.connectors.bigquery.GoogleBigQueryConnector`,
`AnalystStack.connectors.postgres.PostgresConnector`,
`AnalystStack.connectors.databricks.DatabricksConnector`, and any future backend such as
Snowflake) reads and writes through a `SQLAlchemy <https://www.sqlalchemy.org/>`_ ``Engine``
(via ``pandas.read_sql`` / ``DataFrame.to_sql``), using the dialect appropriate for the
destination warehouse: ``sqlalchemy-bigquery`` for BigQuery, the built-in ``psycopg2`` driver
for Postgres, and ``databricks-sqlalchemy`` for Databricks. This keeps the read/write code
path identical across warehouses -- only the connection URL and dialect differ.

Every connector failure raises a subclass of
`AnalystStack.exceptions.errors.DataPackageError`:

* `AnalystStack.exceptions.errors.ConfigurationError` -- required settings (e.g. a project
  id or host) are missing or invalid, usually raised from the connector's ``__init__``.
* `AnalystStack.exceptions.errors.ConnectionError` -- authentication or SQLAlchemy engine
  initialization fails.
* `AnalystStack.exceptions.errors.QueryExecutionError` -- a read query or DataFrame write
  fails.
* `AnalystStack.exceptions.errors.ValidationError` -- input validation fails (e.g. a
  malformed schema/table reference passed to `BaseConnector.write_data`, `list_columns`, or
  `profile_columns`).
"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseConnector(ABC):
    """Abstract base class defining the contract every connector must implement.

    Concrete connectors subclass this and implement `read_data`, `write_data`, and
    `list_tables`. Every concrete connector in this package (BigQuery, Postgres, Databricks)
    also implements ``list_columns(schema, table_id)`` and ``profile_columns(schema,
    table_id)`` with an identical signature -- both returning a DataFrame -- so they are part
    of the shared contract in practice even though they are not declared as
    `abstractmethod`\\ s here (each backend's implementation differs only in the SQL dialect
    used to introspect ``INFORMATION_SCHEMA``). Any future connector should implement all
    three methods so it can be used interchangeably with the existing backends.

    Every metadata method returns a DataFrame with the same columns across every backend,
    regardless of what that backend can cheaply provide -- a column a backend can't populate
    (e.g. Postgres has no table creation timestamp) is filled with ``pd.NA`` rather than
    omitted, so calling code never has to branch on which connector it's talking to.
    """

    @abstractmethod
    def read_data(self, query: str) -> pd.DataFrame:
        """Executes a query and returns a pandas DataFrame.

        Args:
            query: A SQL query string, in the dialect of the destination warehouse.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """

    @abstractmethod
    def write_data(
        self,
        df: pd.DataFrame,
        schema: str,
        table_id: str,
        if_exists: str,
    ) -> None:
        """Writes a DataFrame to a table in the destination system.

        Args:
            df: The DataFrame to write.
            schema: The dataset/schema the destination table lives in.
            table_id: The name of the destination table.
            if_exists: Behavior if the table already exists. Every concrete connector
                accepts ``"append"``, ``"replace"``, or ``"fail"`` and defaults to
                ``"append"``.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the write fails.
        """

    @abstractmethod
    def list_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a schema/dataset, with structural metadata.

        Args:
            schema: The dataset/schema to list tables from.

        Returns:
            A DataFrame with one row per base table and columns ``table_catalog``,
            ``table_schema``, ``table_name``, ``table_type``, ``row_count``, ``size_bytes``,
            ``created``, and ``last_altered``. A column the backend can't cheaply populate
            (see that connector's own docstring for which ones) is filled with ``pd.NA``
            rather than omitted, so the shape is identical across every connector. Empty
            (but still carrying these columns) if the schema/dataset has no base tables.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying metadata
                query fails.
        """
