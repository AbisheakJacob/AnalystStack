"""Tests for the AnalystStack command-line interface."""

import argparse

import pytest

from AnalystStack.cli import handle_format


def _args(language, file, lint=False, dialect="bigquery", level="high", config=None):
    return argparse.Namespace(language=language, file=file, lint=lint, dialect=dialect, level=level, config=config)


def test_cli_format_python_rewrites_file(tmp_path):
    target = tmp_path / "snippet.py"
    target.write_text("x={1:2}\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        handle_format(_args("python", str(target)))

    assert exc.value.code == 0
    assert target.read_text(encoding="utf-8") == "x = {1: 2}\n"


def test_cli_lint_clean_python_exits_zero(tmp_path):
    target = tmp_path / "clean.py"
    target.write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        handle_format(_args("python", str(target), lint=True))

    assert exc.value.code == 0


def test_cli_lint_broken_python_exits_nonzero(tmp_path):
    target = tmp_path / "broken.py"
    target.write_text("def f(:\n    pass\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        handle_format(_args("python", str(target), lint=True))

    assert exc.value.code == 1


def test_cli_missing_file_exits_nonzero():
    with pytest.raises(SystemExit) as exc:
        handle_format(_args("python", "does-not-exist.py"))

    assert exc.value.code == 1


# Points --config at a file that doesn't exist, so tests don't pick up this
# repo's own .sqlfluff (SQLFormatter/CLI auto-detect it otherwise).
_NO_PROJECT_CONFIG = "no-such-config.sqlfluff"


def test_cli_format_sql_rewrites_file_at_high_level(tmp_path):
    target = tmp_path / "query.sql"
    target.write_text("SELECT f.a from foo f\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        handle_format(_args("sql", str(target), dialect="ansi", level="high", config=_NO_PROJECT_CONFIG))

    assert exc.value.code == 0
    assert target.read_text(encoding="utf-8") == "SELECT f.a FROM foo AS f\n"


def test_cli_format_sql_low_level_does_not_add_explicit_aliasing(tmp_path):
    target = tmp_path / "query.sql"
    target.write_text("SELECT f.a from foo f\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        handle_format(_args("sql", str(target), dialect="ansi", level="low", config=_NO_PROJECT_CONFIG))

    assert exc.value.code == 0
    assert target.read_text(encoding="utf-8") == "SELECT f.a FROM foo f\n"


def test_cli_format_sql_destructive_level_eliminates_unused_cte(tmp_path):
    target = tmp_path / "query.sql"
    target.write_text(
        "WITH unused AS (SELECT id FROM orders)\nSELECT id FROM users\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        handle_format(_args("sql", str(target), dialect="bigquery", level="destructive", config=_NO_PROJECT_CONFIG))

    assert exc.value.code == 0
    assert "unused" not in target.read_text(encoding="utf-8")


def test_cli_lint_sql_exits_nonzero_on_violations(tmp_path):
    target = tmp_path / "query.sql"
    target.write_text("SELECT f.a from foo f\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        handle_format(_args("sql", str(target), lint=True, dialect="ansi", level="high", config=_NO_PROJECT_CONFIG))

    assert exc.value.code == 1
