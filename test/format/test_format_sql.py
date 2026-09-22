"""Tests for AnalystStack.format.sql.SQLFormatter."""

import pytest

from AnalystStack.format import FormattingLevel, SQLFormatter

# A table alias that IS referenced, so SQLFluff won't strip it as unused —
# only whether it gets an explicit `AS` depends on the formatting level.
_ALIASED_SQL = "SELECT f.a FROM foo f\n"


def _write(tmp_path, name, contents):
    path = tmp_path / name
    path.write_text(contents, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("level", [FormattingLevel.LOW, FormattingLevel.STANDARD])
def test_low_and_standard_levels_do_not_add_explicit_aliasing(tmp_path, level):
    path = _write(tmp_path, "query.sql", _ALIASED_SQL)
    formatter = SQLFormatter(dialect="ansi", templater="raw", level=level)

    formatted = formatter.format_code(path)

    assert formatted == _ALIASED_SQL


def test_high_level_adds_explicit_aliasing(tmp_path):
    path = _write(tmp_path, "query.sql", _ALIASED_SQL)
    formatter = SQLFormatter(dialect="ansi", templater="raw", level=FormattingLevel.HIGH)

    formatted = formatter.format_code(path)

    assert formatted == "SELECT f.a FROM foo AS f\n"


def test_high_is_the_default_level(tmp_path):
    path = _write(tmp_path, "query.sql", _ALIASED_SQL)
    default_formatter = SQLFormatter(dialect="ansi", templater="raw")

    assert default_formatter.level is FormattingLevel.HIGH
    assert default_formatter.format_code(path) == "SELECT f.a FROM foo AS f\n"


def test_low_level_still_fixes_whitespace_and_casing(tmp_path):
    path = _write(tmp_path, "query.sql", "SELECT f.a from foo f\n")
    formatter = SQLFormatter(dialect="ansi", templater="raw", level=FormattingLevel.LOW)

    formatted = formatter.format_code(path)

    assert formatted == "SELECT f.a FROM foo f\n"


def test_destructive_level_eliminates_unused_ctes_and_redundant_subqueries(tmp_path):
    sql = """
WITH used_cte AS (
    SELECT id, name FROM users
),
unused_cte AS (
    SELECT id FROM orders
)
SELECT a.id, a.name
FROM (SELECT id, name FROM used_cte) AS a
WHERE 1 = 1 AND 2 > 1
"""
    path = _write(tmp_path, "query.sql", sql)
    formatter = SQLFormatter(dialect="bigquery", templater="raw", level=FormattingLevel.DESTRUCTIVE)

    formatted = formatter.format_code(path)

    assert "unused_cte" not in formatted
    assert "orders" not in formatted
    assert "1 = 1" not in formatted
    assert formatted == "SELECT\n    id,\n    name\nFROM users\n"


def test_destructive_level_falls_back_gracefully_on_unrenderable_jinja(tmp_path):
    sql = 'SELECT * FROM {{ ref("my_table") }} WHERE x = 1\n'
    path = _write(tmp_path, "query.sql", sql)
    formatter = SQLFormatter(dialect="bigquery", templater="jinja", level=FormattingLevel.DESTRUCTIVE)

    # Should not raise, and should still apply the underlying SQLFluff fixes.
    formatted = formatter.format_code(path)

    assert '{{ ref("my_table") }}' in formatted


def test_view_errors_scoped_to_level(tmp_path):
    path = _write(tmp_path, "query.sql", _ALIASED_SQL)

    low_violations = SQLFormatter(dialect="ansi", templater="raw", level=FormattingLevel.LOW).view_errors(path)
    high_violations = SQLFormatter(dialect="ansi", templater="raw", level=FormattingLevel.HIGH).view_errors(path)

    assert len(high_violations) > len(low_violations)


def test_dialect_specific_syntax(tmp_path):
    # BigQuery-flavoured backtick-quoted table identifier.
    path = _write(tmp_path, "query.sql", "select 1 from `project.dataset.table`\n")
    formatter = SQLFormatter(dialect="bigquery", templater="raw", level=FormattingLevel.HIGH)

    formatted = formatter.format_code(path)

    assert "`project.dataset.table`" in formatted


def test_invalid_level_raises():
    with pytest.raises(ValueError):
        SQLFormatter(dialect="ansi", level="not-a-real-level")
