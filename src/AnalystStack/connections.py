"""Named connections, resolved from ``config.yaml`` and the ``.env`` cascade.

A connection is described by *name* in ``config.yaml`` at the global, client or product level
(child levels override parents by name)::

    connections:
      fl_pg:
        type: postgres            # postgres | bigquery | databricks | snowflake | duckdb | clickhouse
        env:                      # connector argument -> NAME of an environment variable
          host: FL_PG_HOST
          user: FL_PG_USER
          password: FL_PG_PASSWORD
        options:                  # non-secret literals, passed as-is
          database: analytics
        read_only: true           # the only supported value

Only variable *names* appear in the file. Values are read from the process environment after
`AnalystStack.config.env_cascade.load_env_cascade` has run, are held in memory just long
enough to build the connector, and are never printed, logged or put in an error message.
Connections are always opened read-only: ``read_only: false`` is refused.
"""

import contextlib
import importlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from AnalystStack.config.env_cascade import env_levels, load_env_cascade
from AnalystStack.exceptions.errors import ConfigurationError
from AnalystStack.sql_guard import DIALECT_BY_TYPE

_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_OPEN: list["OpenConnection"] = []

CONNECTOR_CLASSES = {
    "bigquery": ("AnalystStack.connectors.bigquery", "GoogleBigQueryConnector"),
    "postgres": ("AnalystStack.connectors.postgres", "PostgresConnector"),
    "databricks": ("AnalystStack.connectors.databricks", "DatabricksConnector"),
    "snowflake": ("AnalystStack.connectors.snowflake", "SnowflakeConnector"),
    "duckdb": ("AnalystStack.connectors.duckdb", "DuckDBConnector"),
    "clickhouse": ("AnalystStack.connectors.clickhouse", "ClickHouseConnector"),
}


@dataclass
class OpenConnection:
    """A live, read-only connection.

    Attributes:
        name: The connection name from ``config.yaml``.
        type: The connection type.
        dialect: The sqlglot dialect to parse this connection's SQL with.
        connector: The connector instance.
        note: What read-only protection is in force, for display.
    """

    name: str
    type: str
    dialect: str
    connector: Any
    note: str


def load_registry(path: str | Path, root: str | Path | None = None) -> dict[str, dict]:
    """Merges the ``connections:`` blocks that apply to ``path``, child overriding parent.

    Args:
        path: Any file or folder inside the workspace.
        root: The workspace root; found automatically when omitted.

    Returns:
        A mapping of connection name to its spec.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If a config file is unreadable or
            a connection spec is malformed.
    """
    registry: dict[str, dict] = {}
    for level in env_levels(path, root):
        config = level.directory / "config.yaml"
        if not config.is_file():
            continue
        try:
            data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Cannot read {config}.") from exc
        block = data.get("connections") if isinstance(data, dict) else None
        if not block:
            continue
        if not isinstance(block, dict):
            raise ConfigurationError(f"`connections` must be a mapping in {config}.")
        for name, spec in block.items():
            registry[str(name)] = _validate_spec(str(name), spec, config)
    return registry


def _validate_spec(name: str, spec: object, source: Path) -> dict:
    if not isinstance(spec, dict):
        raise ConfigurationError(f"Connection {name!r} must be a mapping ({source}).")
    kind = spec.get("type")
    if kind not in CONNECTOR_CLASSES:
        raise ConfigurationError(
            f"Connection {name!r} has unsupported type {kind!r}; use one of {sorted(CONNECTOR_CLASSES)}."
        )
    if spec.get("read_only", True) is not True:
        raise ConfigurationError(f"Connection {name!r}: only read-only connections are supported.")
    env = spec.get("env") or {}
    if not isinstance(env, dict) or not all(isinstance(v, str) and _ENV_NAME.match(v) for v in env.values()):
        raise ConfigurationError(f"Connection {name!r}: `env` must map arguments to UPPER_CASE variable names.")
    options = spec.get("options") or {}
    if not isinstance(options, dict):
        raise ConfigurationError(f"Connection {name!r}: `options` must be a mapping.")
    return {"type": kind, "env": dict(env), "options": dict(options)}


def list_connections(path: str | Path, root: str | Path | None = None) -> list[dict]:
    """Lists connection names and types (never variable values) for display."""
    return [
        {"name": name, "type": spec["type"], "env_vars": sorted(spec["env"].values())}
        for name, spec in sorted(load_registry(path, root).items())
    ]


def open_connection(name: str, path: str | Path, root: str | Path | None = None) -> OpenConnection:
    """Loads the env cascade, builds the named connector and puts it in read-only mode.

    Args:
        name: A connection name from ``config.yaml``.
        path: Any file or folder inside the workspace (decides which levels apply).
        root: The workspace root; found automatically when omitted.

    Returns:
        The open connection.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If the name is unknown or required
            environment variables are not set. The message lists variable *names* only.
    """
    import os

    from AnalystStack.connectors.readonly import apply_read_only

    registry = load_registry(path, root)
    if name not in registry:
        raise ConfigurationError(f"Unknown connection {name!r}. Known: {sorted(registry) or 'none'}.")
    spec = registry[name]
    load_env_cascade(path, root=root)
    missing = [var for var in spec["env"].values() if not os.environ.get(var)]
    if missing:
        raise ConfigurationError(f"Connection {name!r}: environment variables not set: {', '.join(sorted(missing))}.")
    kwargs = {arg: os.environ[var] for arg, var in spec["env"].items()}
    kwargs.update(spec["options"])
    module_name, class_name = CONNECTOR_CLASSES[spec["type"]]
    try:
        connector_class = getattr(importlib.import_module(module_name), class_name)
    except (ImportError, AttributeError) as exc:
        raise ConfigurationError(
            f"Connection type {spec['type']!r} needs its optional dependencies installed (extra: {spec['type']})."
        ) from exc
    connector = connector_class(**kwargs)
    note = apply_read_only(connector, spec["type"])
    opened = OpenConnection(name, spec["type"], DIALECT_BY_TYPE[spec["type"]], connector, note)
    _OPEN.append(opened)
    return opened


def close_all_connections() -> None:
    """Disposes the engines of every connection opened by `open_connection` in this process.

    The command-line interface calls this when a command ends so that file-based engines
    (DuckDB) release their file and a later command in the same process can reopen it.
    """
    from AnalystStack.connectors.readonly import engine_of

    while _OPEN:
        opened = _OPEN.pop()
        with contextlib.suppress(Exception):  # closing is best effort
            engine_of(opened.connector).dispose()
