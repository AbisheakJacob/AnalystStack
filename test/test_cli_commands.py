"""End-to-end tests for the new command groups, run against a DuckDB file in a temp workspace."""

import re
import sys

import duckdb
import pandas as pd
import pytest
from openpyxl import load_workbook

from AnalystStack.cli import main

TASK = "clients/acme/products/p1/tasks/0001_2026-11-23_demo"
SECRET = "topsecret-env-value"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    db_path = tmp_path / "demo.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE main.orders AS SELECT 1 AS id, 'a' AS region, TIMESTAMP '2020-01-01 00:00:00' AS syncstartdatetime"  # noqa: E501
    )
    con.execute("INSERT INTO main.orders VALUES (2, 'b', TIMESTAMP '2020-01-02 00:00:00')")
    con.close()
    (tmp_path / "global").mkdir()
    (tmp_path / "global" / "config.yaml").write_text(
        f"author: Abisheak Jacob J\nconnections:\n  demo:\n    type: duckdb\n    options:\n      database_path: {db_path.as_posix()}\n",  # noqa: E501
        encoding="utf-8",
    )
    for sub in ("_state", "refs", f"{TASK}/output", f"{TASK}/work"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "_state" / "active_task").write_text(TASK, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["analyststack", *argv])
    main()


def run_exit(monkeypatch, *argv):
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, *argv)
    return exc.value.code


QUERY = (
    "db",
    "query",
    "--connection",
    "demo",
    "--title",
    "Order ids",
    "--description",
    "Lists order ids and regions for the demo.",
)


def test_query_saves_header_and_runs_and_writes_output(workspace, monkeypatch, capsys):
    run(
        monkeypatch,
        *QUERY,
        "--sql",
        "SELECT id, region FROM main.orders ORDER BY id",
        "--out",
        f"{TASK}/output/orders.csv",
    )
    out = capsys.readouterr().out
    assert "rows=2" in out
    saved = workspace / TASK / "sql" / "01_order_ids.sql"
    text = saved.read_text(encoding="utf-8")
    assert re.match(
        r"/\*\nAuthor: Abisheak Jacob J\nDate: \d{4}/\d{2}/\d{2}\nTitle: Order ids\nDescription: Lists order ids and regions for the demo\.\n\*/\n",  # noqa: E501
        text,
    )
    assert (workspace / TASK / "sql" / "_runs.jsonl").read_text(encoding="utf-8").count("\n") == 1
    assert pd.read_csv(workspace / TASK / "output" / "orders.csv").shape == (2, 2)


def test_identical_query_reuses_the_saved_file(workspace, monkeypatch):
    run(monkeypatch, *QUERY, "--sql", "SELECT id FROM main.orders")
    run(monkeypatch, *QUERY, "--sql", "SELECT id FROM main.orders;")
    assert len(list((workspace / TASK / "sql").glob("*.sql"))) == 1
    assert (workspace / TASK / "sql" / "_runs.jsonl").read_text(encoding="utf-8").count("\n") == 2


def test_row_cap_is_applied_and_noted(workspace, monkeypatch, capsys):
    run(monkeypatch, *QUERY, "--sql", "SELECT id FROM main.orders", "--limit", "1")
    out = capsys.readouterr().out
    assert "rows=1" in out and "row cap 1 applied" in out


@pytest.mark.parametrize(
    "sql", ["DELETE FROM main.orders", "SELECT 1; DROP TABLE main.orders", "CREATE TABLE x AS SELECT 1"]
)
def test_write_sql_is_blocked_and_not_saved(workspace, monkeypatch, sql):
    assert run_exit(monkeypatch, *QUERY, "--sql", sql) == 2
    assert not (workspace / TASK / "sql").exists()
    assert (
        duckdb.connect(str(workspace / "demo.duckdb"), read_only=True)
        .execute("SELECT COUNT(*) FROM main.orders")
        .fetchone()[0]  # type: ignore[index]
        == 2
    )


def test_no_active_task_fails_closed_and_scratch_is_the_escape_hatch(workspace, monkeypatch):
    (workspace / "_state" / "active_task").write_text("", encoding="utf-8")
    assert run_exit(monkeypatch, *QUERY, "--sql", "SELECT 1 AS one") == 2
    run(monkeypatch, *QUERY, "--sql", "SELECT 1 AS one", "--scratch")
    assert list((workspace / "_state" / "inbox" / "sql").glob("*.sql"))


def test_description_is_required_and_validated(workspace, monkeypatch):
    bad = ("db", "query", "--connection", "demo", "--title", "T", "--description", "short", "--sql", "SELECT 1")
    assert run_exit(monkeypatch, *bad) == 1


def test_catalog_commands_save_the_sql_they_ran(workspace, monkeypatch, capsys):
    run(monkeypatch, "db", "tables", "--connection", "demo", "--schema", "main")
    run(monkeypatch, "db", "columns", "--connection", "demo", "--schema", "main", "--table", "orders")
    run(monkeypatch, "db", "profile", "--connection", "demo", "--schema", "main", "--table", "orders")
    capsys.readouterr()
    saved = sorted(p.name for p in (workspace / TASK / "sql").glob("*.sql"))
    assert len(saved) >= 3
    for path in (workspace / TASK / "sql").glob("*.sql"):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("/*\nAuthor: Abisheak Jacob J\n") and "Description:" in text


def test_freshness_exit_codes(workspace, monkeypatch, capsys):
    base = ("db", "freshness", "--connection", "demo", "--table", "main.orders")
    run(monkeypatch, *base)
    assert "age_hours=" in capsys.readouterr().out
    assert run_exit(monkeypatch, *base, "--max-age-hours", "1") == 1
    run(monkeypatch, *base, "--max-age-hours", "1000000")


def test_check_sql_needs_no_connection(workspace, monkeypatch, capsys):
    run(monkeypatch, "db", "check-sql", "--sql", "SELECT 1", "--dialect", "postgres")
    assert "OK" in capsys.readouterr().out
    assert run_exit(monkeypatch, "db", "check-sql", "--sql", "DROP TABLE t", "--dialect", "postgres") == 2


def test_env_check_never_prints_values(workspace, monkeypatch, capsys):
    (workspace / "global" / ".env.example").write_text("ONE=\nTWO=\n", encoding="utf-8")
    (workspace / "global" / ".env").write_text(f"ONE={SECRET}\n", encoding="utf-8")
    run(monkeypatch, "env", "check", "--path", str(workspace))
    out = capsys.readouterr().out
    assert "missing key: TWO" in out and SECRET not in out


def test_env_files_and_protected_folders_cannot_be_reached_through_the_cli(workspace, monkeypatch, capsys):
    (workspace / "global" / ".env").write_text(f"ONE={SECRET}\n", encoding="utf-8")
    assert run_exit(monkeypatch, "io", "convert", "global/.env", f"{TASK}/output/x.csv") == 2
    assert run_exit(monkeypatch, "io", "head", "global/.env") == 2
    assert run_exit(monkeypatch, "io", "render", "--file", "global/.env") == 2
    (workspace / "refs" / "f.py").write_text("x={1:2}\n", encoding="utf-8")
    assert run_exit(monkeypatch, "format", "python", "refs/f.py") == 2
    assert (workspace / "refs" / "f.py").read_text(encoding="utf-8") == "x={1:2}\n"
    assert SECRET not in capsys.readouterr().out


def test_io_convert_tidy_compare_summarize_validate(workspace, monkeypatch, capsys):
    out = workspace / TASK / "work"
    pd.DataFrame({"id": [1, 2], "a": [1, 2], "b": [3, 4]}).to_csv(out / "wide.csv", index=False)
    run(monkeypatch, "data", "tidy", f"{TASK}/work/wide.csv", f"{TASK}/work/tidy.csv", "--id-vars", "id")
    assert pd.read_csv(out / "tidy.csv").shape == (4, 3)
    run(
        monkeypatch,
        "data",
        "untidy",
        f"{TASK}/work/tidy.csv",
        f"{TASK}/work/back.csv",
        "--index",
        "id",
        "--columns",
        "variable",
        "--values",
        "value",
    )
    assert list(pd.read_csv(out / "back.csv").columns) == ["id", "a", "b"]
    run(monkeypatch, "io", "convert", f"{TASK}/work/wide.csv", f"{TASK}/work/wide.xlsx")
    run(monkeypatch, "io", "convert", f"{TASK}/work/wide.xlsx", f"{TASK}/work/wide2.csv")
    run(monkeypatch, "data", "compare", f"{TASK}/work/wide.csv", f"{TASK}/work/wide2.csv", "--on", "id")
    assert "IDENTICAL" in capsys.readouterr().out
    pd.DataFrame({"id": [1, 2], "a": [1, 99], "b": [3, 4]}).to_csv(out / "other.csv", index=False)
    assert (
        run_exit(monkeypatch, "data", "compare", f"{TASK}/work/wide.csv", f"{TASK}/work/other.csv", "--on", "id") == 1
    )
    run(monkeypatch, "data", "summarize", f"{TASK}/work/wide.csv")
    (out / "rules.yaml").write_text(
        "- rule: not_null\n  column: id\n- rule: in_range\n  column: a\n  min_value: 0\n  max_value: 10\n",
        encoding="utf-8",
    )
    run(monkeypatch, "data", "validate", f"{TASK}/work/wide.csv", "--rules", f"{TASK}/work/rules.yaml")
    assert "PASSED" in capsys.readouterr().out
    assert (
        run_exit(monkeypatch, "data", "validate", f"{TASK}/work/other.csv", "--rules", f"{TASK}/work/rules.yaml") == 1
    )


def test_validate_refuses_unknown_and_custom_rules(workspace, monkeypatch):
    out = workspace / TASK / "work"
    pd.DataFrame({"id": [1]}).to_csv(out / "d.csv", index=False)
    (out / "bad.yaml").write_text("- rule: custom\n  name: x\n", encoding="utf-8")
    assert run_exit(monkeypatch, "data", "validate", f"{TASK}/work/d.csv", "--rules", f"{TASK}/work/bad.yaml") == 1


def test_render_report_and_branded_excel(workspace, monkeypatch, capsys):
    out = workspace / TASK / "work"
    run(monkeypatch, "io", "render", "--text", "SELECT * FROM {{ table }}", "--var", "table=sales")
    assert "SELECT * FROM sales" in capsys.readouterr().out
    pd.DataFrame({"id": [1, 2], "region": ["a", "b"]}).to_csv(out / "data.csv", index=False)
    run(
        monkeypatch,
        "report",
        "build",
        "--title",
        "Demo",
        "--section",
        f"Data={TASK}/work/data.csv",
        "--out",
        f"{TASK}/output/report.md",
    )
    assert "Demo" in (workspace / TASK / "output" / "report.md").read_text(encoding="utf-8")
    run(monkeypatch, *QUERY, "--sql", "SELECT id FROM main.orders")
    (out / "theme.yaml").write_text("font_name: Arial\nheader_fill: 1F4E79\n", encoding="utf-8")
    run(
        monkeypatch, "excel", "build", "--title", "Orders", "--data", f"{TASK}/work/data.csv", "--note", "Counts exclude test orders.",  # noqa: E501
        "--theme", f"{TASK}/work/theme.yaml", "--out", f"{TASK}/output/orders.xlsx",
    )  # fmt: skip
    book = load_workbook(workspace / TASK / "output" / "orders.xlsx")
    assert book.sheetnames == ["Summary", "Data", "Notes", "Query provenance"]
    provenance = book["Query provenance"]
    assert provenance["A1"].value == "file" and provenance["B2"].value == "Order ids"
    assert book["Data"]["A1"].fill.fgColor.rgb.endswith("1F4E79")


def test_unexpected_errors_do_not_echo_exception_text(workspace, monkeypatch, capsys):
    (workspace / TASK / "work" / "broken.parquet").write_bytes(b"not a parquet file " + SECRET.encode())
    assert run_exit(monkeypatch, "io", "head", f"{TASK}/work/broken.parquet") == 1
    assert SECRET not in capsys.readouterr().err


def test_dialect_probe_sql_is_not_saved(workspace, monkeypatch, capsys):
    run(monkeypatch, "db", "tables", "--connection", "demo", "--schema", "main")
    run(monkeypatch, "db", "freshness", "--connection", "demo", "--table", "main.orders")
    capsys.readouterr()
    saved = [p.read_text(encoding="utf-8") for p in (workspace / TASK / "sql").glob("*.sql")]
    assert saved and not any("UNION ALL BY NAME" in text.upper() for text in saved)
    assert any("MAX(syncstartdatetime)" in text for text in saved)


@pytest.mark.parametrize(
    "template",
    [
        "{{ ''.__class__ }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ cycler.__init__.__globals__.os.environ }}",
        "{{ lipsum.__globals__ }}",
    ],
)
def test_render_is_sandboxed(workspace, monkeypatch, capsys, template):
    code = run_exit(monkeypatch, "io", "render", "--text", template)
    out = capsys.readouterr()
    assert code == 1
    assert out.out.strip() == ""  # nothing was rendered


def test_render_still_works_for_normal_templates(workspace, monkeypatch, capsys):
    run(
        monkeypatch,
        "io",
        "render",
        "--text",
        "SELECT {{ cols|join(', ') }} FROM {{ table }}",
        "--var",
        "table=t",
        "--var",
        "cols=a",
    )
    assert "SELECT" in capsys.readouterr().out
