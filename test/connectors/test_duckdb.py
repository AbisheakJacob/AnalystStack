"""Tests for AnalystStack.connectors.DuckDBConnector.

Unlike the other connector test files, these run against a REAL DuckDB engine
(``:memory:``) instead of mocking ``sqlalchemy.create_engine``. DuckDB is an embedded,
in-process database -- there's no network call or credential to fake, so exercising the
real engine costs nothing and gives genuine functional coverage of the
``list_tables``/``list_columns``/``profile_columns`` contract, rather than mocked
pass-throughs.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from AnalystStack.connectors import DuckDBConnector
from AnalystStack.exceptions.errors import ConnectionError, QueryExecutionError, ValidationError


@pytest.fixture
def connector() -> DuckDBConnector:
    """A fresh in-memory DuckDB connector, with an ``orders`` table pre-populated."""
    db = DuckDBConnector()
    db.write_data(
        pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"], "price": [10.0, None, 30.0]}),
        schema="main",
        table_id="orders",
        if_exists="replace",
    )
    return db


def test_default_database_path_is_in_memory():
    db = DuckDBConnector()
    assert db.database_path == ":memory:"


def test_initialization_wraps_engine_errors():
    """An unwritable/nonexistent path raises ConnectionError, not a raw DuckDB error."""
    with pytest.raises(ConnectionError, match="Client initialization failed"):
        DuckDBConnector(database_path="Z:/nonexistent_dir_xyz/test.db")


def test_read_data_success(connector):
    result = connector.read_data("SELECT * FROM main.orders ORDER BY id")
    assert result["id"].tolist() == [1, 2, 3]


def test_write_data_replace(connector):
    connector.write_data(pd.DataFrame({"id": [9], "name": ["z"], "price": [1.0]}), "main", "orders", "replace")
    result = connector.read_data("SELECT * FROM main.orders")
    assert result["id"].tolist() == [9]


def test_write_data_append(connector):
    connector.write_data(pd.DataFrame({"id": [4], "name": ["d"], "price": [40.0]}), "main", "orders", "append")
    result = connector.read_data("SELECT * FROM main.orders ORDER BY id")
    assert result["id"].tolist() == [1, 2, 3, 4]


def test_read_data_wraps_failures(connector):
    with (
        patch("AnalystStack.connectors.duckdb.query.pd.read_sql", side_effect=Exception("boom")),
        pytest.raises(QueryExecutionError, match="Query execution failed: boom"),
    ):
        connector.read_data("SELECT 1")


def test_write_data_wraps_failures(connector, sample_dataframe):
    with (
        patch("pandas.DataFrame.to_sql", side_effect=Exception("disk full")),
        pytest.raises(QueryExecutionError, match="Failed to write DataFrame to main.orders: disk full"),
    ):
        connector.write_data(sample_dataframe, "main", "orders")


def test_write_data_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.write_data(pd.DataFrame({"id": [1]}), "bad-schema!", "t")


def test_write_data_rejects_invalid_if_exists(connector):
    with pytest.raises(ValueError, match="Invalid if_exists value"):
        connector.write_data(pd.DataFrame({"id": [1]}), "main", "t", if_exists="bogus")


def test_list_tables_includes_the_orders_table(connector):
    result = connector.list_tables("main")

    assert list(result.columns) == [
        "table_catalog",
        "table_schema",
        "table_name",
        "table_type",
        "row_count",
        "size_bytes",
        "created",
        "last_altered",
    ]
    orders_row = result[result["table_name"] == "orders"].iloc[0]
    assert orders_row["table_type"] == "BASE TABLE"
    assert orders_row["row_count"] == 3
    assert pd.isna(orders_row["size_bytes"])
    assert pd.isna(orders_row["created"])


def test_list_tables_empty_schema_has_correct_columns():
    db = DuckDBConnector()
    result = db.list_tables("main")
    assert result.empty
    assert list(result.columns) == [
        "table_catalog",
        "table_schema",
        "table_name",
        "table_type",
        "row_count",
        "size_bytes",
        "created",
        "last_altered",
    ]


def test_list_tables_rejects_invalid_identifier(connector):
    with pytest.raises(ValidationError):
        connector.list_tables("bad-schema!")


def test_list_columns(connector):
    result = connector.list_columns("main", "orders")

    assert result["column_name"].tolist() == ["id", "name", "price"]
    assert result["ordinal_position"].tolist() == [1, 2, 3]
    assert list(result.columns) == [
        "table_schema",
        "table_name",
        "column_name",
        "ordinal_position",
        "data_type",
        "is_nullable",
        "column_default",
    ]


def test_list_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.list_columns("main", "bad table!")


def test_profile_columns(connector):
    result = connector.profile_columns("main", "orders")

    assert result["row_count"].tolist() == [3, 3, 3]
    price_row = result[result["column_name"] == "price"].iloc[0]
    assert price_row["non_null_count"] == 2
    assert price_row["null_count"] == 1
    assert price_row["fill_rate_pct"] == pytest.approx(66.67)


def test_profile_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.profile_columns("main", "bad table!")
