"""Uses standard dataclasses to pull from environment variables, avoiding hardcoded secrets"""

import os
from dataclasses import dataclass, field


@dataclass
class BigQuerySettings:
    """Manages default settings for the BigQuery environment."""

    gcp_project_id: str | None = field(default_factory=lambda: os.getenv("GCP_PROJECT_ID"))
    gbq_project_id: str | None = field(default_factory=lambda: os.getenv("GBQ_PROJECT_ID"))
    credentials_path: str | None = field(default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    location: str = field(default_factory=lambda: os.getenv("BQ_LOCATION", "US"))


@dataclass
class DatabricksSettings:
    """Manages default settings for the Databricks environment."""

    server_hostname: str | None = field(default_factory=lambda: os.getenv("DATABRICKS_SERVER_HOSTNAME"))
    http_path: str | None = field(default_factory=lambda: os.getenv("DATABRICKS_HTTP_PATH"))
    access_token: str | None = field(default_factory=lambda: os.getenv("DATABRICKS_ACCESS_TOKEN"))
    catalog: str | None = field(default_factory=lambda: os.getenv("DATABRICKS_CATALOG"))
    schema: str | None = field(default_factory=lambda: os.getenv("DATABRICKS_SCHEMA"))


@dataclass
class PostgresSettings:
    """Manages default settings for the Postgres environment."""

    host: str | None = field(default_factory=lambda: os.getenv("POSTGRES_HOST"))
    port: str | None = field(default_factory=lambda: os.getenv("POSTGRES_PORT"))
    database: str | None = field(default_factory=lambda: os.getenv("POSTGRES_DATABASE"))
    user: str | None = field(default_factory=lambda: os.getenv("POSTGRES_USER"))
    password: str | None = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD"))


@dataclass
class DuckDBSettings:
    """Manages default settings for the DuckDB environment."""

    database_path: str | None = field(default_factory=lambda: os.getenv("DUCKDB_DATABASE_PATH"))


@dataclass
class SnowflakeSettings:
    """Manages default settings for the Snowflake environment."""

    account: str | None = field(default_factory=lambda: os.getenv("SNOWFLAKE_ACCOUNT"))
    user: str | None = field(default_factory=lambda: os.getenv("SNOWFLAKE_USER"))
    password: str | None = field(default_factory=lambda: os.getenv("SNOWFLAKE_PASSWORD"))
    database: str | None = field(default_factory=lambda: os.getenv("SNOWFLAKE_DATABASE"))
    warehouse: str | None = field(default_factory=lambda: os.getenv("SNOWFLAKE_WAREHOUSE"))
    schema: str | None = field(default_factory=lambda: os.getenv("SNOWFLAKE_SCHEMA"))
    role: str | None = field(default_factory=lambda: os.getenv("SNOWFLAKE_ROLE"))
