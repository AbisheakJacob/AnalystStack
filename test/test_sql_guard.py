"""Tests for the read-only SQL guard: one case per rejection class."""

import pytest

from AnalystStack.exceptions.errors import ReadOnlyViolationError
from AnalystStack.sql_guard import assert_read_only

ACCEPTED = [
    ("SELECT 1", "postgres"),
    ("SELECT 1;", "postgres"),
    ("SELECT a, COUNT(*) FROM s.t WHERE x > 1 GROUP BY a ORDER BY 2 LIMIT 5", "bigquery"),
    ("WITH a AS (SELECT 1 AS n) SELECT * FROM a UNION ALL SELECT 2", "postgres"),
    ("SELECT MAX(syncstartdatetime) FROM ds.orders", "clickhouse"),
    ("-- leading comment\nSELECT * FROM t", "duckdb"),
]


@pytest.mark.parametrize(("sql", "dialect"), ACCEPTED)
def test_plain_reads_are_accepted(sql, dialect):
    assert assert_read_only(sql, dialect) is not None


REJECTED = {
    "insert": ("INSERT INTO t VALUES (1)", "postgres"),
    "update": ("UPDATE t SET a = 1", "postgres"),
    "delete": ("DELETE FROM t", "postgres"),
    "merge": ("MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN DELETE", "postgres"),
    "create": ("CREATE TABLE t (a INT)", "postgres"),
    "create_as_select": ("CREATE TABLE t AS SELECT 1", "duckdb"),
    "drop": ("DROP TABLE t", "postgres"),
    "alter": ("ALTER TABLE t ADD COLUMN b INT", "postgres"),
    "truncate": ("TRUNCATE TABLE t", "postgres"),
    "grant": ("GRANT SELECT ON t TO someone", "postgres"),
    "copy": ("COPY t TO '/tmp/x'", "postgres"),
    "call": ("CALL do_something()", "postgres"),
    "exec": ("EXEC sp_who", "postgres"),
    "vacuum": ("VACUUM", "postgres"),
    "set": ("SET search_path = x", "postgres"),
    "multi_statement": ("SELECT 1; DROP TABLE t", "postgres"),
    "two_selects": ("SELECT 1; SELECT 2", "postgres"),
    "select_into": ("SELECT * INTO new_t FROM t", "postgres"),
    "for_update": ("SELECT * FROM t FOR UPDATE", "postgres"),
    "writable_cte_delete": ("WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x", "postgres"),
    "writable_cte_insert": ("WITH x AS (INSERT INTO t VALUES (1) RETURNING *) SELECT * FROM x", "postgres"),
    "clickhouse_url": ("SELECT * FROM url('http://example.com/x', 'CSV')", "clickhouse"),
    "clickhouse_file": ("SELECT * FROM file('x.csv')", "clickhouse"),
    "clickhouse_s3": ("SELECT * FROM s3('https://b/x', 'CSV')", "clickhouse"),
    "clickhouse_remote": ("SELECT * FROM remote('host', db.t)", "clickhouse"),
    "pg_read_file": ("SELECT pg_read_file('/etc/passwd')", "postgres"),
    "dblink": ("SELECT * FROM dblink('dbname=x', 'select 1') AS t(a int)", "postgres"),
    "lo_import": ("SELECT lo_import('/etc/passwd')", "postgres"),
    "duckdb_read_csv": ("SELECT * FROM read_csv('x.csv')", "duckdb"),
    "duckdb_read_parquet": ("SELECT * FROM read_parquet('a.parquet')", "duckdb"),
    "duckdb_read_json": ("SELECT * FROM read_json_auto('a.json')", "duckdb"),
    "duckdb_quoted_file_path": ("SELECT * FROM 'data.csv'", "duckdb"),
    "duckdb_quoted_url": ("SELECT * FROM 'https://example.com/a.parquet'", "duckdb"),
    "duckdb_double_quoted_glob": ('SELECT * FROM "exports/*.csv"', "duckdb"),
    "unparseable": ("SELECT (", "postgres"),
    "empty": ("   ", "postgres"),
    "nul_byte": ("SELECT 1\x00; DROP TABLE t", "postgres"),
}


@pytest.mark.parametrize("name", sorted(REJECTED))
def test_non_reads_are_rejected(name):
    sql, dialect = REJECTED[name]
    with pytest.raises(ReadOnlyViolationError):
        assert_read_only(sql, dialect)


def test_error_message_never_echoes_the_sql():
    secret = "SELECT 'topsecret-value' FROM ("
    with pytest.raises(ReadOnlyViolationError) as exc:
        assert_read_only(secret, "postgres")
    assert "topsecret-value" not in str(exc.value)
