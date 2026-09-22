import os
from enum import Enum
from typing import Any, cast

import sqlfluff
import sqlglot
from sqlfluff.core.config import FluffConfig
from sqlglot.errors import OptimizeError, ParseError
from sqlglot.optimizer.eliminate_ctes import eliminate_ctes
from sqlglot.optimizer.eliminate_subqueries import eliminate_subqueries
from sqlglot.optimizer.merge_subqueries import merge_subqueries
from sqlglot.optimizer.simplify import simplify

from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class FormattingLevel(str, Enum):  # noqa: UP042 - StrEnum needs Python 3.11+; this package supports 3.9+
    """How aggressively `SQLFormatter` is allowed to rewrite SQL.

    * ``LOW`` — cosmetic only: whitespace, indentation, and keyword/identifier
      casing. Never touches query structure, so it's safe to run on
      generated or unfamiliar SQL without reviewing the diff.
    * ``STANDARD`` — SQLFluff's own curated ``core`` rule group: the
      uncontroversial correctness/style rules (consistent quoting, trailing
      commas, redundant parentheses, etc.) that most teams agree on, without
      opinionated conventions like forced aliasing.
    * ``HIGH`` — SQLFluff's full rule set, including opinionated conventions
      (explicit aliasing, join qualification, disallowed constructs). This is
      the default and matches AnalystStack's historical formatting behavior.
    * ``DESTRUCTIVE`` — everything in ``HIGH``, plus a structural rewrite pass
      (via [sqlglot](https://sqlglot.com/)) that eliminates unused CTEs,
      collapses redundant/nested subqueries, and simplifies always-true or
      always-false predicates. Unlike the other levels this can change the
      *shape* of the query, not just its whitespace — review the diff before
      trusting it in production. It degrades gracefully (falling back to
      ``HIGH``-only output) on SQL it can't safely parse, e.g. unrendered
      Jinja templates.
    """

    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    DESTRUCTIVE = "destructive"


# SQLFluff rule groups to enable at each level. "core" and "all" are groups
# SQLFluff itself defines; "layout"/"capitalisation" are the two groups that
# only ever touch whitespace and casing, never query structure.
_LEVEL_RULES: dict[FormattingLevel, str] = {
    FormattingLevel.LOW: "layout, capitalisation",
    FormattingLevel.STANDARD: "core",
    FormattingLevel.HIGH: "all",
    FormattingLevel.DESTRUCTIVE: "all",
}

# sqlglot and SQLFluff agree on most dialect names (bigquery, databricks,
# postgres, snowflake, ...) but diverge on a few — map the ones that differ.
_SQLGLOT_DIALECT_ALIASES: dict[str, str] = {
    "sparksql": "spark",
    # SQLFluff's generic dialect is "ansi"; sqlglot's is the empty string.
    "ansi": "",
}


class SQLFormatter:
    """Handles SQL linting and formatting using SQLFluff (and, for the
    ``destructive`` level, [sqlglot](https://sqlglot.com/)).

    Wraps [SQLFluff](https://sqlfluff.com/) and supports any SQLFluff dialect
    and templater. Unlike `PythonFormatter`, which operates on code passed as
    strings, `SQLFormatter`'s methods read from and write to files on disk.

    Example:
        ```python
        from AnalystStack.format import FormattingLevel, SQLFormatter

        # House style, e.g. for BigQuery
        fmt = SQLFormatter(dialect="bigquery", templater="jinja", config_path=".sqlfluff")

        # A Postgres query, formatted lightly (whitespace/casing only)
        light = SQLFormatter(dialect="postgres", level=FormattingLevel.LOW)

        # A Databricks query, pared down to its logical minimum
        aggressive = SQLFormatter(dialect="databricks", level=FormattingLevel.DESTRUCTIVE)
        ```
    """

    def __init__(
        self,
        dialect: str = "bigquery",
        templater: str = "jinja",
        config_path: str | None = None,
        level: FormattingLevel | str = FormattingLevel.HIGH,
    ):
        """
        Initializes the formatter and builds its SQLFluff configuration.

        Args:
            dialect: SQL dialect SQLFluff (and, at the ``destructive`` level,
                sqlglot) should lint/format against, e.g. ``"bigquery"``,
                ``"databricks"``, ``"postgres"``, or any other dialect
                SQLFluff supports (see `sqlfluff dialects`).
            templater: Templater SQLFluff should use to render the SQL before
                linting/formatting, e.g. ``"jinja"`` or ``"raw"``.
            config_path: Path to a ``.sqlfluff`` file containing project-level
                rule overrides. If given and the file exists, its settings are
                merged with ``dialect``/``templater``/``level``; otherwise
                only those three are used. Pass this pointing at a
                ``.sqlfluff`` file to enforce your project's house style —
                AnalystStack ships one at the repo root as a starting point.
            level: How aggressively to rewrite the SQL — see `FormattingLevel`.
                Defaults to `FormattingLevel.HIGH`, SQLFluff's full rule set.
        """
        self.dialect = dialect
        self.templater = templater
        self.config_path = config_path
        self.level = FormattingLevel(level)

        # Build the configuration override dictionary. SQLFluff expects a flat
        # mapping of config keys (not nested under a "core" section).
        self.config_overrides: dict[str, Any] = {
            "dialect": self.dialect,
            "templater": self.templater,
            "rules": _LEVEL_RULES[self.level],
        }

        # If the user has a .sqlfluff file (e.g., in their repo root), point to it
        if self.config_path and os.path.exists(self.config_path):
            logger.info(f"Using SQLFluff config from {self.config_path}")
            self.config = FluffConfig.from_path(self.config_path, overrides=self.config_overrides)
        else:
            self.config = FluffConfig(overrides=self.config_overrides)

    def view_errors(self, file_path: str) -> list[dict[str, Any]]:
        """
        Returns SQLFluff lint violations for a file.

        Reads the file at ``file_path`` and lints its contents with SQLFluff
        using this formatter's configured dialect, templater, rule level, and
        (if given) ``.sqlfluff`` config. Which violations are reported scales
        with `level` — e.g. a `FormattingLevel.LOW` formatter only reports
        whitespace/casing issues, while `FormattingLevel.HIGH` reports the
        full rule set.

        Args:
            file_path: Path to the SQL file to lint.

        Returns:
            A list of lint violation dicts as returned by `sqlfluff.lint`
            (empty if the file is clean).

        Raises:
            Exception: Re-raises whatever reading the file or `sqlfluff.lint`
                raises, after logging the failure.

        Example:
            ```python
            fmt = SQLFormatter(dialect="bigquery", templater="jinja", config_path=".sqlfluff")
            violations = fmt.view_errors("query.sql")
            ```
        """
        logger.info(f"Linting SQL file: {file_path}")

        try:
            with open(file_path) as f:
                sql_string = f.read()

            lint_results = sqlfluff.lint(sql_string, config=self.config)

            if not lint_results:
                logger.info("SQL is clean! No errors found.")

            return lint_results

        except Exception as e:
            logger.error(f"SQLFluff linting failed: {e}")
            raise

    def format_code(self, file_path: str, output_path: str | None = None) -> str:
        """
        Fixes a SQL file's formatting using SQLFluff, at this formatter's
        configured `level`.

        Reads the file at ``file_path``, applies SQLFluff's automatic fixes
        for the configured dialect/level, and — at `FormattingLevel.DESTRUCTIVE`
        — follows up with a structural rewrite pass (eliminating unused CTEs,
        collapsing redundant subqueries, and simplifying constant predicates)
        before writing the result either back to ``file_path`` in place, or to
        ``output_path`` if one is given (leaving the original file untouched).

        Args:
            file_path: Path to the SQL file to read and fix.
            output_path: If given, the fixed SQL is written here instead of
                overwriting ``file_path``.

        Returns:
            The formatted SQL, as a string.

        Raises:
            Exception: Re-raises whatever reading/writing the file or
                `sqlfluff.fix` raises, after logging the failure.

        Example:
            ```python
            fmt = SQLFormatter(dialect="bigquery", templater="jinja", config_path=".sqlfluff")
            fmt.format_code("query.sql")                     # overwrites in place
            fmt.format_code("query.sql", "query.fixed.sql")  # writes a copy
            ```
        """
        logger.info(f"Formatting SQL file: {file_path} (dialect={self.dialect}, level={self.level.value})")

        try:
            with open(file_path) as f:
                sql_string = f.read()

            formatted_sql = sqlfluff.fix(sql_string, config=self.config)

            if self.level is FormattingLevel.DESTRUCTIVE:
                formatted_sql = self._apply_destructive_rewrite(formatted_sql)

            # Write output
            if output_path:
                with open(output_path, "w") as f:
                    f.write(formatted_sql)
            else:
                # overwrite original file
                with open(file_path, "w") as f:
                    f.write(formatted_sql)

            return formatted_sql

        except Exception as e:
            logger.error(f"SQLFluff formatting failed: {e}")
            raise

    def _apply_destructive_rewrite(self, sql_string: str) -> str:
        """
        Best-effort structural cleanup on top of `sql_string`, via sqlglot.

        Eliminates CTEs and subqueries nothing references, merges/collapses
        nested subqueries that add no value, and simplifies always-true or
        always-false predicates. Structural changes like these can only be
        made safely against fully-rendered SQL, so if ``sql_string`` can't be
        parsed as such (e.g. it still contains unrendered Jinja) — or if
        `self.dialect` isn't one sqlglot recognises — this logs a warning and
        returns ``sql_string`` unchanged rather than raising.

        Args:
            sql_string: Already SQLFluff-fixed SQL to rewrite further.

        Returns:
            The rewritten SQL (re-run through SQLFluff to restore house-style
            casing/indentation), or ``sql_string`` unchanged if the rewrite
            couldn't be safely performed.
        """
        sqlglot_dialect = _SQLGLOT_DIALECT_ALIASES.get(self.dialect, self.dialect)

        try:
            tree = sqlglot.parse_one(sql_string, dialect=sqlglot_dialect)
            tree = eliminate_subqueries(tree)
            tree = merge_subqueries(tree)
            tree = eliminate_ctes(tree)
            tree = simplify(tree)
            rewritten_sql = cast(str, tree.sql(dialect=sqlglot_dialect, pretty=True))
        except (ParseError, OptimizeError, ValueError) as e:
            logger.warning(f"Destructive rewrite skipped, falling back to '{FormattingLevel.HIGH.value}' output: {e}")
            return sql_string

        # sqlglot's own pretty-printer doesn't know this project's house
        # style, so re-run the rewritten SQL back through SQLFluff.
        try:
            return sqlfluff.fix(rewritten_sql, config=self.config)
        except Exception as e:
            logger.warning(f"Could not re-apply house style after destructive rewrite: {e}")
            return rewritten_sql
