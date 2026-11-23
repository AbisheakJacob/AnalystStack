"""The Facade (The Final Connector)

Combines the ClickHouse client, query, metadata and profiling managers behind the shared
`BaseConnector` contract. Read-only by design.
"""

import pandas as pd

from AnalystStack.connectors.base import BaseConnector
from AnalystStack.connectors.clickhouse.client import ClickHouseClientWrapper
from AnalystStack.connectors.clickhouse.metadata import MetadataManager
from AnalystStack.connectors.clickhouse.profiling import ProfileManager
from AnalystStack.connectors.clickhouse.query import QueryManager
from AnalystStack.exceptions.errors import ConfigurationError


class ClickHouseConnector(BaseConnector):
    """Read-only connector for ClickHouse, over HTTP(S) via ``clickhouse-connect``.

    Unverified against a live server: the SQL and the connection URL were written from
    ClickHouse's documented ``system`` tables and the ``clickhouse-connect`` dialect and are
    covered by offline tests only. Check ``list_tables``/``list_columns`` against a real
    instance before relying on them.

    Args:
        host: The server hostname. Required.
        port: The HTTP(S) port (default 8123).
        database: The default database.
        user: The username.
        password: The password.
        secure: Use HTTPS.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If ``host`` is missing.
        AnalystStack.exceptions.errors.ConnectionError: If the connection cannot be opened.

    Example:
        ```python
        from AnalystStack.connectors import ClickHouseConnector

        ch = ClickHouseConnector(host="ch.example.com", user="reader", password="...", secure=True)
        df = ch.read_data("SELECT MAX(syncstartdatetime) FROM tool.stores")
        ```
    """

    def __init__(
        self,
        host: str | None = None,
        port: str | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        secure: bool | str = False,
    ):
        if not host:
            raise ConfigurationError("A ClickHouse host must be provided.")
        use_tls = secure if isinstance(secure, bool) else str(secure).strip().lower() in ("1", "true", "yes")
        self._client_wrapper = ClickHouseClientWrapper(host, port, database, user, password, use_tls)
        self._query_manager = QueryManager(self._client_wrapper)
        self._metadata_manager = MetadataManager(self._query_manager)
        self._profile_manager = ProfileManager(self._query_manager, self._metadata_manager)

    def read_data(self, query: str) -> pd.DataFrame:
        """Executes a ClickHouse SQL query and returns the result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails.
        """
        return self._query_manager.execute_read(query)

    def write_data(self, df: pd.DataFrame, schema: str, table_id: str, if_exists: str = "append") -> None:
        """Not supported: this connector is read-only.

        Raises:
            AnalystStack.exceptions.errors.ConfigurationError: Always.
        """
        raise ConfigurationError("ClickHouseConnector is read-only; write_data is not supported.")

    def list_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a ClickHouse database; see `MetadataManager.fetch_tables`."""
        return self._metadata_manager.fetch_tables(schema)

    def list_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns column metadata for a table; see `MetadataManager.fetch_columns`."""
        return self._metadata_manager.fetch_columns(schema, table_id)

    def profile_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Profiles a table's columns; see `ProfileManager.profile_columns`."""
        return self._profile_manager.profile_columns(schema, table_id)
