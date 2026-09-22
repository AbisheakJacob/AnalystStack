"""Tests for AnalystStack.connectors.SnowflakeConnector.

``sqlalchemy.create_engine`` (and ``pandas.read_sql`` / ``DataFrame.to_sql``) are patched so
these tests never make a network call to a real Snowflake account.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from AnalystStack.connectors import SnowflakeConnector
from AnalystStack.exceptions.errors import ConfigurationError, ConnectionError, QueryExecutionError, ValidationError

ACCOUNT, USER, PASSWORD, DATABASE, WAREHOUSE = "xy12345", "analyst", "secret", "analytics", "compute_wh"

# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------


@pytest.fixture
def mock_engine():
    """Patches ``create_engine`` used inside the client wrapper."""
    with patch("AnalystStack.connectors.snowflake.client.create_engine") as mock_create_engine:
        engine_instance = MagicMock()
        mock_create_engine.return_value = engine_instance
        yield engine_instance


@pytest.fixture
def connector(mock_engine):
    """A pre-initialised connector wired to the mocked engine."""
    return SnowflakeConnector(account=ACCOUNT, user=USER, password=PASSWORD, database=DATABASE, warehouse=WAREHOUSE)


# ---------------------------------------------------------
# Initialisation
# ---------------------------------------------------------


def test_initialization_missing_settings(monkeypatch):
    """Missing connection settings (args and env) raise ConfigurationError."""
    for var in (
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_WAREHOUSE",
    ):
        monkeypatch.delenv(var, raising=False)
    empty_settings = SimpleNamespace(
        account=None, user=None, password=None, database=None, warehouse=None, schema=None, role=None
    )
    with (
        patch("AnalystStack.connectors.snowflake.connector.SnowflakeSettings", return_value=empty_settings),
        pytest.raises(ConfigurationError, match="account / user / password / database / warehouse"),
    ):
        SnowflakeConnector()


def test_initialization_wraps_engine_errors():
    """A failure while creating/connecting the engine raises ConnectionError."""
    with (
        patch("AnalystStack.connectors.snowflake.client.create_engine", side_effect=RuntimeError("bad credentials")),
        pytest.raises(ConnectionError, match="Client initialization failed"),
    ):
        SnowflakeConnector(account=ACCOUNT, user=USER, password=PASSWORD, database=DATABASE, warehouse=WAREHOUSE)


# ---------------------------------------------------------
# read_data
# ---------------------------------------------------------


def test_read_data_success(connector, mock_engine, sample_dataframe):
    query = "SELECT * FROM fake_table"
    with patch("AnalystStack.connectors.snowflake.query.pd.read_sql", return_value=sample_dataframe) as mock_read_sql:
        result_df = connector.read_data(query)

    mock_read_sql.assert_called_once_with(query, mock_engine)
    pd.testing.assert_frame_equal(result_df, sample_dataframe)


def test_read_data_failure(connector, mock_engine):
    with (
        patch("AnalystStack.connectors.snowflake.query.pd.read_sql", side_effect=Exception("warehouse suspended")),
        pytest.raises(QueryExecutionError, match="Query execution failed: warehouse suspended"),
    ):
        connector.read_data("SELECT * FROM fake_table")


# ---------------------------------------------------------
# write_data
# ---------------------------------------------------------


def test_write_data_uses_engine(connector, mock_engine, sample_dataframe):
    with patch("pandas.DataFrame.to_sql") as mock_to_sql:
        connector.write_data(df=sample_dataframe, schema="public", table_id="products", if_exists="replace")

    mock_to_sql.assert_called_once_with(
        name="products", con=mock_engine, schema="public", if_exists="replace", index=False
    )


def test_write_data_rejects_invalid_table_reference(connector, sample_dataframe):
    with pytest.raises(ValidationError):
        connector.write_data(df=sample_dataframe, schema="bad-schema!", table_id="t")


def test_write_data_rejects_invalid_if_exists(connector, sample_dataframe):
    with pytest.raises(ValueError, match="Invalid if_exists value"):
        connector.write_data(df=sample_dataframe, schema="public", table_id="t", if_exists="bogus")


def test_write_data_wraps_failures(connector, mock_engine, sample_dataframe):
    with (
        patch("pandas.DataFrame.to_sql", side_effect=Exception("disk full")),
        pytest.raises(QueryExecutionError, match="Failed to write DataFrame to public.products: disk full"),
    ):
        connector.write_data(df=sample_dataframe, schema="public", table_id="products")


# ---------------------------------------------------------
# metadata & profiling
# ---------------------------------------------------------


def test_list_tables(connector, mock_engine):
    tables_df = pd.DataFrame(
        {
            "table_catalog": ["analytics"],
            "table_schema": ["public"],
            "table_name": ["orders"],
            "table_type": ["BASE TABLE"],
            "row_count": [1000],
            "size_bytes": [20480],
            "created": [pd.Timestamp("2026-01-01", tz="UTC")],
            "last_altered": [pd.Timestamp("2026-02-01", tz="UTC")],
        }
    )
    with patch("AnalystStack.connectors.snowflake.query.pd.read_sql", return_value=tables_df):
        result = connector.list_tables("public")
    pd.testing.assert_frame_equal(result, tables_df)


def test_list_tables_rejects_invalid_identifier(connector):
    with pytest.raises(ValidationError):
        connector.list_tables("bad-schema!")


def test_list_columns(connector, mock_engine):
    columns_df = pd.DataFrame(
        {
            "table_schema": ["public"] * 3,
            "table_name": ["products"] * 3,
            "column_name": ["id", "name", "price"],
            "ordinal_position": [1, 2, 3],
            "data_type": ["NUMBER", "TEXT", "FLOAT"],
            "is_nullable": ["NO", "YES", "YES"],
            "column_default": [None, None, None],
        }
    )
    with patch("AnalystStack.connectors.snowflake.query.pd.read_sql", return_value=columns_df):
        result = connector.list_columns("public", "products")
    pd.testing.assert_frame_equal(result, columns_df)


def test_list_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.list_columns("public", "bad table!")


def test_profile_columns(connector, mock_engine):
    columns_df = pd.DataFrame(
        {
            "table_schema": ["public"] * 2,
            "table_name": ["products"] * 2,
            "column_name": ["id", "name"],
            "ordinal_position": [1, 2],
            "data_type": ["NUMBER", "TEXT"],
            "is_nullable": ["NO", "YES"],
            "column_default": [None, None],
        }
    )
    counts_df = pd.DataFrame({"row_count": [100], "id": [100], "name": [95]})

    with patch("AnalystStack.connectors.snowflake.query.pd.read_sql", side_effect=[columns_df, counts_df]):
        result = connector.profile_columns("public", "products")

    assert result["row_count"].tolist() == [100, 100]
    assert result["non_null_count"].tolist() == [100, 95]
    assert result["null_count"].tolist() == [0, 5]
    assert result["fill_rate_pct"].tolist() == [100.0, 95.0]


def test_profile_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.profile_columns("public", "bad table!")
