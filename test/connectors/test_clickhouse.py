"""Offline tests for the ClickHouse connector: SQL generation, URL construction and read-only behaviour.

No server is contacted. Behaviour against a live ClickHouse is NOT verified by these tests.
"""

from typing import Any

import pandas as pd
import pytest

from AnalystStack.connectors.clickhouse.client import ClickHouseClientWrapper
from AnalystStack.connectors.clickhouse.connector import ClickHouseConnector
from AnalystStack.connectors.clickhouse.metadata import MetadataManager
from AnalystStack.connectors.clickhouse.profiling import ProfileManager
from AnalystStack.exceptions.errors import ConfigurationError, ConnectionError, ValidationError
from AnalystStack.sql_guard import assert_read_only


class _RecordingQueryManager:
    def __init__(self, frames):
        self.frames = list(frames)
        self.queries = []

    def execute_read(self, query):
        self.queries.append(query)
        return self.frames.pop(0)


def test_host_is_required():
    with pytest.raises(ConfigurationError):
        ClickHouseConnector()


def test_unreachable_server_raises_connection_error_without_hitting_a_network_listener():
    with pytest.raises(ConnectionError):
        ClickHouseClientWrapper(host="127.0.0.1", port="1", database="d", user="u", password="p")


def test_write_data_is_not_supported(monkeypatch):
    connector = ClickHouseConnector.__new__(ClickHouseConnector)
    with pytest.raises(ConfigurationError):
        connector.write_data(pd.DataFrame({"a": [1]}), "s", "t")


def test_list_tables_sql_is_a_guarded_read_and_filters_views():
    manager: Any = _RecordingQueryManager([pd.DataFrame()])
    frame = MetadataManager(manager).fetch_tables("tool")
    sql = manager.queries[0]
    assert "system.tables" in sql and "database = 'tool'" in sql and "'View'" in sql
    assert_read_only(sql, "clickhouse")
    assert list(frame.columns)[:3] == ["table_catalog", "table_schema", "table_name"] and frame.empty


def test_list_columns_sql_and_validation():
    manager: Any = _RecordingQueryManager([pd.DataFrame()])
    MetadataManager(manager).fetch_columns("tool", "stores")
    assert_read_only(manager.queries[0], "clickhouse")
    with pytest.raises(ValidationError):
        MetadataManager(manager).fetch_columns("tool", "stores; DROP TABLE x")


def test_profile_computes_fill_rate():
    columns = pd.DataFrame(
        {
            "table_schema": ["tool", "tool"],
            "table_name": ["t", "t"],
            "column_name": ["a", "b"],
            "ordinal_position": [1, 2],
            "data_type": ["Int32", "Nullable(String)"],
            "is_nullable": ["NO", "YES"],
            "column_default": ["", ""],
        }
    )
    counts = pd.DataFrame({"row_count": [10], "a": [10], "b": [5]})
    manager: Any = _RecordingQueryManager([columns, counts])
    profile = ProfileManager(manager, MetadataManager(manager)).profile_columns("tool", "t")
    assert list(profile["fill_rate_pct"]) == [100.0, 50.0]
    assert_read_only(manager.queries[1], "clickhouse")
