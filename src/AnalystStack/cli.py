"""The ``analyststack`` command-line entry point.

Installed as the console script ``analyststack`` (see the ``[options.entry_points]``
section of ``setup.cfg``). Currently exposes a single ``format`` command that lints or
formats a Python or SQL file, backed by
:class:`~AnalystStack.format.python.PythonFormatter` /
:class:`~AnalystStack.format.sql.SQLFormatter`.

Example:
    ```bash
    analyststack format python path/to/file.py                                    # format in place
    analyststack format sql    path/to/query.sql --lint                           # lint only, non-zero exit on errors
    analyststack format sql    path/to/query.sql --dialect postgres --level low   # light touch-up only
    analyststack format sql    path/to/query.sql --dialect databricks --level destructive
    ```
"""

import argparse
import os
import sys

from AnalystStack.format import FormattingLevel, PythonFormatter, SQLFormatter

_DEFAULT_SQLFLUFF_CONFIG = ".sqlfluff"


def _format_python(file_path: str, lint: bool) -> None:
    """Lint or format a Python file (operates on the file's contents as a string)."""
    formatter = PythonFormatter()
    with open(file_path, encoding="utf-8") as f:
        raw_code = f.read()

    if lint:
        errors = formatter.view_errors(raw_code)
        if not errors:
            print("OK: code is clean, no errors found.")
            sys.exit(0)
        print(f"ERROR: found {len(errors)} issue(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    formatted = formatter.format_code(raw_code)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(formatted)
    print("OK: formatting complete.")
    sys.exit(0)


def _format_sql(file_path: str, lint: bool, dialect: str, level: str, config_path: str | None) -> None:
    """Lint or format a SQL file (SQLFluff operates directly on the file)."""
    # Auto-detect a repo-root .sqlfluff file if the caller didn't point at one.
    if config_path is None and os.path.exists(_DEFAULT_SQLFLUFF_CONFIG):
        config_path = _DEFAULT_SQLFLUFF_CONFIG

    formatter = SQLFormatter(dialect=dialect, config_path=config_path, level=FormattingLevel(level))

    if lint:
        violations = formatter.view_errors(file_path)
        if not violations:
            print("OK: code is clean, no errors found.")
            sys.exit(0)
        print(f"ERROR: found {len(violations)} issue(s):")
        for v in violations:
            print(f"  - Line {v.get('start_line_no')}: {v.get('description')}")
        sys.exit(1)

    formatter.format_code(file_path)  # fixes in place
    print("OK: formatting complete.")
    sys.exit(0)


def handle_format(args: argparse.Namespace) -> None:
    """Handles the ``analyststack format <language> <file> [--lint]`` command.

    Dispatches to :class:`~AnalystStack.format.python.PythonFormatter` for
    ``language="python"`` (operating on the file's contents as a string) or
    :class:`~AnalystStack.format.sql.SQLFormatter` for ``language="sql"`` (which
    operates on the file path directly). With ``--lint``, prints violations and exits
    non-zero if any are found instead of rewriting the file.

    Args:
        args: The parsed CLI arguments; must have ``language`` (``"python"`` or
            ``"sql"``), ``file`` (the path to lint/format), ``lint`` (a bool flag), and
            (for ``"sql"``) ``dialect``, ``level``, and ``config`` — see ``main`` for
            what each means and defaults to.

    Raises:
        SystemExit: Always — with code 0 on success/clean lint, or 1 if the file is
            missing, lint violations were found, or formatting failed.
    """
    file_path = args.file
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)

    verb = "Linting" if args.lint else "Formatting"
    print(f"{verb} {args.language.upper()} file: {file_path}...")

    try:
        if args.language == "python":
            _format_python(file_path, args.lint)
        else:
            _format_sql(file_path, args.lint, args.dialect, args.level, args.config)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 - surface any formatter failure to the CLI user
        print(f"ERROR: operation failed: {e}")
        sys.exit(1)


def main() -> None:
    """The main entry point for the CLI."""
    parser = argparse.ArgumentParser(prog="analyststack", description="Data analyst utilities CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    format_parser = subparsers.add_parser("format", help="Lint or format SQL/Python files.")
    format_parser.add_argument("language", choices=["sql", "python"], help="The language to format.")
    format_parser.add_argument("file", help="Path to the file you want to format.")
    format_parser.add_argument("--lint", action="store_true", help="View errors only (do not overwrite file).")
    format_parser.add_argument(
        "--dialect",
        default="bigquery",
        help="SQL dialect to format against, e.g. bigquery, databricks, postgres, snowflake, ... "
        "(any SQLFluff dialect). Ignored for --language python.",
    )
    format_parser.add_argument(
        "--level",
        choices=[level.value for level in FormattingLevel],
        default=FormattingLevel.HIGH.value,
        help="How aggressively to rewrite SQL: 'low' touches whitespace/casing only, 'standard' "
        "applies SQLFluff's uncontroversial core rules, 'high' (default) applies its full rule "
        "set, and 'destructive' additionally eliminates unused CTEs/subqueries and simplifies "
        "constant predicates. Ignored for --language python.",
    )
    format_parser.add_argument(
        "--config",
        default=None,
        help="Path to a .sqlfluff config file. Defaults to ./.sqlfluff if it exists. Ignored for --language python.",
    )
    format_parser.set_defaults(func=handle_format)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
