"""Tests for the env cascade, the SQL log, freshness and the connection registry."""

import json
import os
from datetime import UTC, datetime

import duckdb
import pandas as pd
import pytest

from AnalystStack.config.env_cascade import check_env, env_levels, load_env_cascade
from AnalystStack.connections import list_connections, load_registry, open_connection
from AnalystStack.connectors.freshness import check_freshness, freshness_sql
from AnalystStack.exceptions.errors import ConfigurationError, QueryExecutionError, ValidationError
from AnalystStack.sqllog import (
    build_header,
    header_is_complete,
    parse_header,
    read_author,
    read_provenance,
    record_run,
    save_query,
)

SECRET = "s3cr3t-value-must-never-appear"


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "global").mkdir()
    (tmp_path / "global" / "config.yaml").write_text("author: Test Author\n", encoding="utf-8")
    product = tmp_path / "clients" / "acme" / "products" / "p1"
    (product / "tasks").mkdir(parents=True)
    return tmp_path


def test_cascade_child_overrides_parent_and_values_are_not_returned(workspace):
    (workspace / "global" / ".env").write_text(f"A=global\nB=global\nSHARED={SECRET}\n", encoding="utf-8")
    (workspace / "clients" / "acme" / ".env").write_text("B=client\nC=client\n", encoding="utf-8")
    product = workspace / "clients" / "acme" / "products" / "p1"
    (product / ".env").write_text("C=product\n", encoding="utf-8")
    target: dict[str, str] = {}
    keys = load_env_cascade(product / "tasks", root=workspace, environ=target)
    assert keys == ["A", "B", "C", "SHARED"]
    assert target["A"] == "global" and target["B"] == "client" and target["C"] == "product"
    assert SECRET not in repr(keys)


def test_cascade_does_not_override_values_set_by_the_real_environment(workspace):
    (workspace / "global" / ".env").write_text("FROM_DEPLOY=file\n", encoding="utf-8")
    target = {"FROM_DEPLOY": "injected"}
    assert load_env_cascade(workspace, root=workspace, environ=target) == []
    assert target["FROM_DEPLOY"] == "injected"


def test_cascade_levels_follow_the_path(workspace):
    assert [lvl.name for lvl in env_levels(workspace, workspace)] == ["global"]
    deep = workspace / "clients" / "acme" / "products" / "p1" / "tasks"
    assert [lvl.name for lvl in env_levels(deep, workspace)] == ["global", "client", "product"]


def test_check_env_reports_names_only(workspace):
    (workspace / "global" / ".env.example").write_text("# comment\nONE=\nTWO=\n", encoding="utf-8")
    (workspace / "global" / ".env").write_text(f"ONE={SECRET}\nTHREE=x\n", encoding="utf-8")
    report = check_env(workspace, workspace)[0]
    assert report["missing"] == ["TWO"] and report["extra"] == ["THREE"]
    assert SECRET not in json.dumps(report)


def test_check_env_without_env_files(workspace):
    (workspace / "global" / ".env.example").write_text("ONE=\n", encoding="utf-8")
    report = check_env(workspace, workspace)[0]
    assert report["env_present"] is False and report["missing"] == ["ONE"]


def test_cascade_outside_workspace_raises(tmp_path):
    with pytest.raises(ConfigurationError):
        env_levels(tmp_path, None)


def test_header_has_exactly_the_four_fields():
    header = build_header("Abisheak Jacob J", "Store list", "Lists active stores for the test.", datetime(2026, 11, 23))
    assert header == (
        "/*\nAuthor: Abisheak Jacob J\nDate: 2026/11/23\nTitle: Store list\nDescription: Lists active stores for the test.\n*/\n"  # noqa: E501
    )


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("", "A long enough description"),
        ("T", "short"),
        ("T", "contains */ marker here"),
        ("two\nlines", "A long enough description"),
    ],
)
def test_header_rejects_bad_fields(title, description):
    with pytest.raises(ValidationError):
        build_header("A", title, description)


def test_save_query_names_dedupes_and_records_runs(tmp_path):
    first = save_query(tmp_path, "SELECT 1", "First query", "Returns the number one, for testing.", author="A")
    assert first.path.name == "01_first_query.sql" and not first.reused
    text = first.path.read_text(encoding="utf-8")
    assert header_is_complete(text) and text.rstrip().endswith("SELECT 1;")
    again = save_query(tmp_path, "SELECT   1 ;", "Other title", "A different description, same SQL.", author="A")
    assert again.reused and again.path == first.path
    second = save_query(tmp_path, "SELECT 2", "Second", "Returns the number two, for testing.", author="A")
    assert second.path.name == "02_second.sql"
    record_run(tmp_path, first, connection="demo", rows=1, ok=True, seconds=0.1)
    frame = read_provenance(tmp_path)
    assert list(frame["title"]) == ["First query"] and list(frame["connection"]) == ["demo"]


def test_parse_header_roundtrip_and_incomplete_file():
    text = build_header("A", "T", "Line one of the description.\nLine two follows.") + "SELECT 1;\n"
    fields = parse_header(text)
    assert fields["Title"] == "T" and "Line two follows." in fields["Description"]
    assert not header_is_complete("SELECT 1;")


def test_read_author_requires_config(workspace, tmp_path_factory):
    assert read_author(workspace) == "Test Author"
    (workspace / "global" / "config.yaml").write_text("other: 1\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        read_author(workspace)


class _Stub:
    def __init__(self, value):
        self.value = value

    def read_data(self, query):
        self.query = query
        return pd.DataFrame({"max_value": [self.value]})


def test_freshness_age_and_staleness():
    now = datetime(2026, 11, 23, 12, tzinfo=UTC)
    result = check_freshness(_Stub(pd.Timestamp("2026-11-23 06:00")), "ds.orders", now=now)
    assert result.age_hours == pytest.approx(6.0)
    assert result.is_fresh(24) and not result.is_fresh(1)
    assert result.sql == "SELECT MAX(syncstartdatetime) AS max_value FROM ds.orders"


def test_freshness_empty_table_is_not_fresh():
    result = check_freshness(_Stub(pd.NaT), "ds.orders")
    assert result.max_value is None and not result.is_fresh(10**6)


@pytest.mark.parametrize("table", ["ds.orders; DROP TABLE x", "a.b.c.d", "bad name"])
def test_freshness_rejects_bad_table_names(table):
    with pytest.raises(ValidationError):
        freshness_sql(table)


def _duck_workspace(workspace, extra_yaml=""):
    db_path = workspace / "demo.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE main.orders AS SELECT 1 AS id, TIMESTAMP '2020-01-01 00:00:00' AS syncstartdatetime")
    con.close()
    config = f"author: Test Author\nconnections:\n  demo:\n    type: duckdb\n    options:\n      database_path: {db_path.as_posix()}\n{extra_yaml}"  # noqa: E501
    (workspace / "global" / "config.yaml").write_text(config, encoding="utf-8")
    return db_path


def test_registry_lists_names_without_values(workspace):
    _duck_workspace(workspace)
    (workspace / "global" / "config.yaml").write_text(
        "connections:\n  pg:\n    type: postgres\n    env:\n      host: PG_HOST\n      password: PG_PASSWORD\n",
        encoding="utf-8",
    )
    rows = list_connections(workspace, workspace)
    assert rows == [{"name": "pg", "type": "postgres", "env_vars": ["PG_HOST", "PG_PASSWORD"]}]


def test_registry_rejects_write_connections_and_bad_types(workspace):
    (workspace / "global" / "config.yaml").write_text(
        "connections:\n  x:\n    type: duckdb\n    read_only: false\n", encoding="utf-8"
    )
    with pytest.raises(ConfigurationError):
        load_registry(workspace, workspace)
    (workspace / "global" / "config.yaml").write_text("connections:\n  x:\n    type: oracle\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_registry(workspace, workspace)


def test_missing_env_vars_are_named_not_valued(workspace, monkeypatch):
    (workspace / "global" / "config.yaml").write_text(
        "connections:\n  pg:\n    type: postgres\n    env:\n      host: PG_HOST_UNSET_FOR_TEST\n", encoding="utf-8"
    )
    monkeypatch.delenv("PG_HOST_UNSET_FOR_TEST", raising=False)
    with pytest.raises(ConfigurationError, match="PG_HOST_UNSET_FOR_TEST"):
        open_connection("pg", workspace, workspace)


def test_duckdb_connection_is_read_only_at_the_session_level(workspace):
    _duck_workspace(workspace)
    conn = open_connection("demo", workspace, workspace)
    assert "read only" in conn.note
    assert len(conn.connector.read_data("SELECT * FROM main.orders")) == 1
    with pytest.raises(QueryExecutionError):
        conn.connector.read_data("CREATE TABLE main.should_fail (a INT)")


def test_unknown_connection_name(workspace):
    _duck_workspace(workspace)
    with pytest.raises(ConfigurationError):
        open_connection("nope", workspace, workspace)
    assert os.environ.get("SECRET_NOT_SET") is None
