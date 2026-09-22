"""Dedicated to executing postgres SQL and moving data"""

import pandas as pd

from AnalystStack.connectors.postgres.client import PostgresClientWrapper
from AnalystStack.exceptions.errors import QueryExecutionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class QueryManager:
    """Handles read and write data operations to Postgres.

    Every method runs through `AnalystStack.connectors.postgres.client.PostgresClientWrapper`'s
    SQLAlchemy ``Engine`` via ``pandas.read_sql`` / ``DataFrame.to_sql``, so the code path is
    identical to the other backends in this package -- only the dialect differs.

    Args:
        client_wrapper: The `PostgresClientWrapper` supplying the SQLAlchemy engine.
    """

    def __init__(self, client_wrapper: PostgresClientWrapper):
        self.wrapper = client_wrapper

    def execute_read(self, query: str) -> pd.DataFrame:
        """Runs a SQL query and returns the result as a DataFrame.

        Args:
            query: A PostgreSQL query string.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """
        try:
            logger.info(f"Executing read query: {query[:100]}...")
            return pd.read_sql(query, self.wrapper.engine)

        except Exception as e:
            logger.exception("Query Execution Failed")
            raise QueryExecutionError(f"Query execution failed: {e}") from e

    def execute_write(self, df: pd.DataFrame, dataset_id: str, table_id: str, if_exists: str = "append") -> None:
        """Writes a DataFrame to a schema-qualified Postgres table.

        Args:
            df: The DataFrame to write.
            dataset_id: The Postgres schema the destination table lives in.
            table_id: The destination table name.
            if_exists: Behavior if the table already exists: ``"append"`` (default),
                ``"replace"``, or ``"fail"``.

        Raises:
            ValueError: If `if_exists` is not one of ``"append"``, ``"replace"``, or
                ``"fail"``.
            AnalystStack.exceptions.errors.QueryExecutionError: If the write fails.
        """
        table_ref = f"{dataset_id}.{table_id}"

        if if_exists not in ("append", "replace", "fail"):
            raise ValueError(f"Invalid if_exists value: {if_exists}")

        try:
            logger.info(f"Writing {len(df)} rows to {table_ref} ({if_exists})..")
            df.to_sql(name=table_id, con=self.wrapper.engine, schema=dataset_id, if_exists=if_exists, index=False)
            logger.info(f"Write complete for {table_ref}.")
        except Exception as e:
            logger.exception(f"Failed to write DataFrame to {table_ref}")
            raise QueryExecutionError(f"Failed to write DataFrame to {table_ref}: {e}") from e
