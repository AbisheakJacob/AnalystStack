"""The Bigquery Engine (Composition Module)

Isolates authentication and API connection logic"""

from google.cloud import bigquery
from google.oauth2 import service_account
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from AnalystStack.exceptions.errors import ConnectionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class BigQueryClientWrapper:
    """Builds and wraps both connections BigQuery reads/writes need: a SQLAlchemy ``Engine``
    (via the ``sqlalchemy-bigquery`` dialect) for queries, and a native
    ``google.cloud.bigquery.Client`` for bulk loads.

    Owns the low-level connection setup: constructing the SQLAlchemy ``URL``, creating the
    ``Engine``, eagerly opening a test connection so failures surface immediately at
    construction time rather than on the first query, and building the native client used
    by `AnalystStack.connectors.bigquery.query.QueryManager.execute_write` for
    ``load_table_from_dataframe`` (bulk loads, not row-by-row DML `INSERT`, are the only
    way to write more than a trivial number of rows to BigQuery in reasonable time -- see
    `AnalystStack.connectors.bigquery.query.QueryManager` for why).

    Attributes:
        engine: The underlying SQLAlchemy ``Engine``, used by
            `AnalystStack.connectors.bigquery.query.QueryManager` and the metadata/profiling
            managers to run queries.
        bigquery_client: The native ``google.cloud.bigquery.Client``, used only for
            `load_table_from_dataframe` bulk loads.
    """

    def __init__(self, gcp_project_id: str, credentials_path: str | None = None):
        """Creates and validates the SQLAlchemy engine and native client for a BigQuery project.

        Args:
            gcp_project_id: The GCP project used for billing/authentication.
            credentials_path: Path to a service-account JSON key file. If None, both the
                engine and the native client authenticate via Application Default
                Credentials (ADC).

        Raises:
            AnalystStack.exceptions.errors.ConnectionError: If constructing the engine,
                opening the test connection, or constructing the native client fails (e.g.
                invalid project id or credentials).
        """
        self.gcp_project_id = gcp_project_id
        self.credentials_path = credentials_path
        try:
            url = URL.create(
                "bigquery",
                host=gcp_project_id,
                query={"credentials_path": credentials_path} if credentials_path else {},
            )
            self._engine: Engine = create_engine(url)
            with self._engine.connect():
                pass

            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                self._bigquery_client = bigquery.Client(project=gcp_project_id, credentials=credentials)
            else:
                self._bigquery_client = bigquery.Client(project=gcp_project_id)

            logger.info(f"BigQuery client initialized for project {self.gcp_project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise ConnectionError(f"Client initialization failed: {e}") from e

    @property
    def engine(self) -> Engine:
        """The underlying SQLAlchemy `Engine` used to run reads and metadata/profiling queries."""
        return self._engine

    @property
    def bigquery_client(self) -> bigquery.Client:
        """The native ``google.cloud.bigquery.Client`` used for `load_table_from_dataframe` bulk loads."""
        return self._bigquery_client
