"""Tests for AnalystStack.connectors.DatabricksConnector.

``sqlalchemy.create_engine`` (and ``pandas.read_sql`` / ``DataFrame.to_sql``) are patched so
these tests never make a network call to a real Databricks workspace.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from AnalystStack.connectors import DatabricksConnector
from AnalystStack.exceptions.errors import ConfigurationError, ConnectionError, QueryExecutionError, ValidationError

SERVER_HOSTNAME = "example.cloud.databricks.com"
HTTP_PATH = "/sql/1.0/warehouses/abc123"
ACCESS_TOKEN = "dapi_test_token"
CATALOG = "main"
SCHEMA = "analytics"

# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------


@pytest.fixture
def mock_engine():
    """Patches ``create_engine`` used inside the client wrapper."""
    with patch("AnalystStack.connectors.databricks.client.create_engine") as mock_create_engine:
        engine_instance = MagicMock()
        mock_create_engine.return_value = engine_instance
        yield engine_instance


@pytest.fixture
def connector(mock_engine):
    """A pre-initialised connector wired to the mocked engine."""
    return DatabricksConnector(
        server_hostname=SERVER_HOSTNAME,
        http_path=HTTP_PATH,
        access_token=ACCESS_TOKEN,
        catalog=CATALOG,
        schema=SCHEMA,
    )


# ---------------------------------------------------------
# Initialisation
# ---------------------------------------------------------


def test_initialization_missing_settings(monkeypatch):
    """Missing connection settings (args and env) raise ConfigurationError."""
    for var in (
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_ACCESS_TOKEN",
        "DATABRICKS_CATALOG",
        "DATABRICKS_SCHEMA",
    ):
        monkeypatch.delenv(var, raising=False)
    empty_settings = SimpleNamespace(server_hostname=None, http_path=None, access_token=None, catalog=None, schema=None)
    with (
        patch("AnalystStack.connectors.databricks.connector.DatabricksSettings", return_value=empty_settings),
        pytest.raises(ConfigurationError, match="server_hostname, http_path, access_token, catalog, and schema"),
    ):
        DatabricksConnector()


def test_initialization_wraps_engine_errors():
    """A failure while creating/connecting the engine raises ConnectionError."""
    with (
        patch("AnalystStack.connectors.databricks.client.create_engine", side_effect=RuntimeError("bad token")),
        pytest.raises(ConnectionError, match="Client initialization failed"),
    ):
        DatabricksConnector(
            server_hostname=SERVER_HOSTNAME,
            http_path=HTTP_PATH,
            access_token=ACCESS_TOKEN,
            catalog=CATALOG,
            schema=SCHEMA,
        )


# ---------------------------------------------------------
# read_data
# ---------------------------------------------------------


def test_read_data_success(connector, mock_engine, sample_dataframe):
    query = "SELECT * FROM fake_table"
    with patch("AnalystStack.connectors.databricks.query.pd.read_sql", return_value=sample_dataframe) as mock_read_sql:
        result_df = connector.read_data(query)

    mock_read_sql.assert_called_once_with(query, mock_engine)
    pd.testing.assert_frame_equal(result_df, sample_dataframe)


def test_read_data_failure(connector, mock_engine):
    with (
        patch("AnalystStack.connectors.databricks.query.pd.read_sql", side_effect=Exception("cluster terminated")),
        pytest.raises(QueryExecutionError, match="Query execution failed: cluster terminated"),
    ):
        connector.read_data("SELECT * FROM fake_table")


# ---------------------------------------------------------
# write_data
# ---------------------------------------------------------


def test_write_data_uses_engine(connector, mock_engine, sample_dataframe):
    with patch("pandas.DataFrame.to_sql") as mock_to_sql:
        connector.write_data(df=sample_dataframe, schema=SCHEMA, table_id="products", if_exists="replace")

    mock_to_sql.assert_called_once_with(
        name="products", con=mock_engine, schema=SCHEMA, if_exists="replace", index=False
    )


def test_write_data_rejects_invalid_table_reference(connector, sample_dataframe):
    with pytest.raises(ValidationError):
        connector.write_data(df=sample_dataframe, schema="bad-schema!", table_id="t")


def test_write_data_rejects_invalid_if_exists(connector, sample_dataframe):
    with pytest.raises(ValueError, match="Invalid if_exists value"):
        connector.write_data(df=sample_dataframe, schema=SCHEMA, table_id="t", if_exists="bogus")


# ---------------------------------------------------------
# metadata & profiling
# ---------------------------------------------------------


def test_list_tables(connector, mock_engine):
    raw_tables_df = pd.DataFrame(
        {
            "table_catalog": [CATALOG],
            "table_schema": [SCHEMA],
            "table_name": ["orders"],
            "table_type": ["BASE TABLE"],
            "created": [pd.Timestamp("2026-01-01", tz="UTC")],
            "last_altered": [pd.Timestamp("2026-02-01", tz="UTC")],
        }
    )
    with patch("AnalystStack.connectors.databricks.query.pd.read_sql", return_value=raw_tables_df):
        result = connector.list_tables(SCHEMA)

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
    assert result["row_count"].isna().all()
    assert result["size_bytes"].isna().all()
    assert result["table_name"].tolist() == ["orders"]


def test_list_tables_rejects_invalid_identifier(connector):
    with pytest.raises(ValidationError):
        connector.list_tables("bad-schema!")


def test_list_columns(connector, mock_engine):
    columns_df = pd.DataFrame(
        {
            "table_schema": [SCHEMA] * 3,
            "table_name": ["products"] * 3,
            "column_name": ["id", "name", "price"],
            "ordinal_position": [1, 2, 3],
            "data_type": ["BIGINT", "STRING", "DOUBLE"],
            "is_nullable": ["NO", "YES", "YES"],
            "column_default": [None, None, None],
        }
    )
    with patch("AnalystStack.connectors.databricks.query.pd.read_sql", return_value=columns_df):
        result = connector.list_columns(SCHEMA, "products")
    pd.testing.assert_frame_equal(result, columns_df)


def test_list_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.list_columns(SCHEMA, "bad table!")


def test_profile_columns(connector, mock_engine):
    columns_df = pd.DataFrame(
        {
            "table_schema": [SCHEMA] * 2,
            "table_name": ["products"] * 2,
            "column_name": ["id", "name"],
            "ordinal_position": [1, 2],
            "data_type": ["BIGINT", "STRING"],
            "is_nullable": ["NO", "YES"],
            "column_default": [None, None],
        }
    )
    counts_df = pd.DataFrame({"row_count": [100], "id": [100], "name": [95]})

    with patch("AnalystStack.connectors.databricks.query.pd.read_sql", side_effect=[columns_df, counts_df]):
        result = connector.profile_columns(SCHEMA, "products")

    assert result["row_count"].tolist() == [100, 100]
    assert result["non_null_count"].tolist() == [100, 95]
    assert result["null_count"].tolist() == [0, 5]
    assert result["fill_rate_pct"].tolist() == [100.0, 95.0]


def test_profile_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.profile_columns(SCHEMA, "bad table!")
