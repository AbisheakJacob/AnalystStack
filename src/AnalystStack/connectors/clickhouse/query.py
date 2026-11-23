"""Dedicated to executing ClickHouse SQL (read only)"""

import pandas as pd

from AnalystStack.connectors.clickhouse.client import ClickHouseClientWrapper
from AnalystStack.exceptions.errors import QueryExecutionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class QueryManager:
    """Handles read operations against ClickHouse.

    There is deliberately no write method: this connector is read-only.

    Args:
        client_wrapper: The `ClickHouseClientWrapper` supplying the SQLAlchemy engine.
    """

    def __init__(self, client_wrapper: ClickHouseClientWrapper):
        self.wrapper = client_wrapper

    def execute_read(self, query: str) -> pd.DataFrame:
        """Runs a SQL query and returns the result as a DataFrame.

        Args:
            query: A ClickHouse SQL query string.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to execute.
        """
        try:
            logger.debug(f"Executing read query: {query[:100]}...")
            return pd.read_sql(query, self.wrapper.engine)
        except Exception as e:
            logger.exception("Query execution failed")
            raise QueryExecutionError(f"Query execution failed: {e}") from e
