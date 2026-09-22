"""Tests for AnalystStack.connectors.GoogleBigQueryConnector.

``sqlalchemy.create_engine`` (and ``pandas.read_sql``) are patched for reads/metadata, and
``google.cloud.bigquery.Client`` is patched for writes, so these tests never make a network
call to GCP.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from google.cloud import bigquery

from AnalystStack.connectors import GoogleBigQueryConnector
from AnalystStack.exceptions.errors import ConfigurationError, ConnectionError, QueryExecutionError, ValidationError

GCP_PROJECT = "test-gcp-project-123"
GBQ_PROJECT = "test-gbq-project-123"

# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------


@pytest.fixture
def mock_engine():
    """Patches ``create_engine`` used inside the client wrapper."""
    with patch("AnalystStack.connectors.bigquery.client.create_engine") as mock_create_engine:
        engine_instance = MagicMock()
        mock_create_engine.return_value = engine_instance
        yield engine_instance


@pytest.fixture
def mock_bigquery_client(mock_engine):
    """Patches the native ``bigquery.Client`` used inside the client wrapper for load jobs."""
    with patch("AnalystStack.connectors.bigquery.client.bigquery.Client") as mock_client_cls:
        client_instance = MagicMock()
        mock_client_cls.return_value = client_instance
        yield client_instance


@pytest.fixture
def connector(mock_bigquery_client):
    """A pre-initialised connector wired to the mocked engine and native client."""
    return GoogleBigQueryConnector(gcp_project_id=GCP_PROJECT, gbq_project_id=GBQ_PROJECT)


# ---------------------------------------------------------
# Initialisation
# ---------------------------------------------------------


def test_initialization_missing_project_id(monkeypatch):
    """A missing project id (arg and env) raises ConfigurationError."""
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    empty_settings = SimpleNamespace(gcp_project_id=None, gbq_project_id=None, credentials_path=None)
    with (
        patch("AnalystStack.connectors.bigquery.connector.BigQuerySettings", return_value=empty_settings),
        pytest.raises(ConfigurationError, match="A GCP project_id must be provided"),
    ):
        GoogleBigQueryConnector(gcp_project_id=None)


def test_initialization_wraps_engine_errors():
    """A failure while creating/connecting the engine raises ConnectionError."""
    with (
        patch("AnalystStack.connectors.bigquery.client.create_engine", side_effect=RuntimeError("bad credentials")),
        pytest.raises(ConnectionError, match="Client initialization failed"),
    ):
        GoogleBigQueryConnector(gcp_project_id=GCP_PROJECT)


# ---------------------------------------------------------
# read_data
# ---------------------------------------------------------


def test_read_data_success(connector, mock_engine, sample_dataframe):
    query = "SELECT * FROM fake_table"
    with patch("AnalystStack.connectors.bigquery.query.pd.read_sql", return_value=sample_dataframe) as mock_read_sql:
        result_df = connector.read_data(query)

    mock_read_sql.assert_called_once_with(query, mock_engine)
    pd.testing.assert_frame_equal(result_df, sample_dataframe)


def test_read_data_failure(connector, mock_engine):
    with (
        patch("AnalystStack.connectors.bigquery.query.pd.read_sql", side_effect=Exception("GCP Network Timeout")),
        pytest.raises(QueryExecutionError, match="Query execution failed: GCP Network Timeout"),
    ):
        connector.read_data("SELECT * FROM fake_table")


# ---------------------------------------------------------
# write_data
# ---------------------------------------------------------


def test_write_data_uses_load_job(connector, mock_bigquery_client, sample_dataframe):
    """Writes must go through a native `load_table_from_dataframe` load job -- not
    `DataFrame.to_sql` / DML `INSERT` -- since DML writes take minutes even for a moderate
    row count (one query job per ~1,000 rows, each with several seconds of overhead)."""
    load_job = MagicMock()
    mock_bigquery_client.load_table_from_dataframe.return_value = load_job

    connector.write_data(df=sample_dataframe, schema="test_dataset", table_id="test_table", if_exists="replace")

    mock_bigquery_client.load_table_from_dataframe.assert_called_once()
    call_args = mock_bigquery_client.load_table_from_dataframe.call_args
    assert call_args.args[0] is sample_dataframe
    assert call_args.args[1] == f"{GBQ_PROJECT}.test_dataset.test_table"
    job_config = call_args.kwargs["job_config"]
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert job_config.autodetect is True
    load_job.result.assert_called_once()


def test_write_data_wraps_load_job_errors(connector, mock_bigquery_client, sample_dataframe):
    mock_bigquery_client.load_table_from_dataframe.side_effect = Exception("quota exceeded")
    with pytest.raises(QueryExecutionError, match="Failed to write DataFrame"):
        connector.write_data(df=sample_dataframe, schema="test_dataset", table_id="test_table")


def test_gbq_project_id_defaults_to_gcp_project_id(mock_bigquery_client):
    """When only `gcp_project_id` is given, `gbq_project_id` must fall back to it instead of
    staying `None` -- otherwise metadata/profiling/write queries interpolate the literal
    string "None" into a `project.dataset.table` reference."""
    connector = GoogleBigQueryConnector(gcp_project_id=GCP_PROJECT)
    assert connector.gbq_project_id == GCP_PROJECT


def test_write_data_rejects_invalid_table_reference(connector, sample_dataframe):
    with pytest.raises(ValidationError):
        connector.write_data(df=sample_dataframe, schema="bad-dataset!", table_id="t")


def test_write_data_rejects_invalid_if_exists(connector, sample_dataframe):
    with pytest.raises(ValueError, match="Invalid if_exists value"):
        connector.write_data(df=sample_dataframe, schema="test_dataset", table_id="t", if_exists="bogus")


# ---------------------------------------------------------
# metadata & profiling
# ---------------------------------------------------------


def test_list_tables(connector, mock_engine):
    tables_df = pd.DataFrame(
        {
            "table_catalog": ["test-gbq-project-123"],
            "table_schema": ["test_dataset"],
            "table_name": ["orders"],
            "table_type": ["BASE TABLE"],
            "row_count": [1000],
            "size_bytes": [20480],
            "created": [pd.Timestamp("2026-01-01", tz="UTC")],
            "last_altered": [pd.Timestamp("2026-02-01", tz="UTC")],
        }
    )
    with patch("AnalystStack.connectors.bigquery.query.pd.read_sql", return_value=tables_df):
        result = connector.list_tables("test_dataset")
    pd.testing.assert_frame_equal(result, tables_df)


def test_list_tables_rejects_invalid_identifier(connector):
    with pytest.raises(ValidationError):
        connector.list_tables("bad-dataset!")


def test_list_columns(connector, mock_engine):
    columns_df = pd.DataFrame(
        {
            "table_schema": ["test_dataset"] * 3,
            "table_name": ["test_table"] * 3,
            "column_name": ["id", "name", "price"],
            "ordinal_position": [1, 2, 3],
            "data_type": ["INT64", "STRING", "FLOAT64"],
            "is_nullable": ["NO", "YES", "YES"],
            "column_default": [None, None, None],
        }
    )
    with patch("AnalystStack.connectors.bigquery.query.pd.read_sql", return_value=columns_df):
        result = connector.list_columns("test_dataset", "test_table")
    pd.testing.assert_frame_equal(result, columns_df)


def test_list_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.list_columns("test_dataset", "bad table!")


def test_profile_columns(connector, mock_engine):
    columns_df = pd.DataFrame(
        {
            "table_schema": ["test_dataset"] * 2,
            "table_name": ["test_table"] * 2,
            "column_name": ["id", "name"],
            "ordinal_position": [1, 2],
            "data_type": ["INT64", "STRING"],
            "is_nullable": ["NO", "YES"],
            "column_default": [None, None],
        }
    )
    counts_df = pd.DataFrame({"row_count": [100], "id": [100], "name": [95]})

    with patch("AnalystStack.connectors.bigquery.query.pd.read_sql", side_effect=[columns_df, counts_df]):
        result = connector.profile_columns("test_dataset", "test_table")

    assert result["row_count"].tolist() == [100, 100]
    assert result["non_null_count"].tolist() == [100, 95]
    assert result["null_count"].tolist() == [0, 5]
    assert result["fill_rate_pct"].tolist() == [100.0, 95.0]


def test_profile_columns_rejects_invalid_table_reference(connector):
    with pytest.raises(ValidationError):
        connector.profile_columns("test_dataset", "bad table!")
