"""Helpers shared by the command-line command modules.

Every command goes through two things defined here:

* `guarded`, which turns library errors into short messages and exit codes without a
  traceback (a policy or read-only refusal exits ``2``, any other expected failure exits
  ``1``) and never prints the text of an unexpected exception, because driver errors can echo
  connection details;
* `read_frame` / `write_frame`, which apply the path policy in `AnalystStack.paths` *before*
  any file is opened.
"""

import functools
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from AnalystStack.connections import close_all_connections
from AnalystStack.exceptions.errors import (
    ConnectionError,
    DataPackageError,
    PathPolicyError,
    ReadOnlyViolationError,
    ValidationError,
)
from AnalystStack.paths import check_read, check_write
from AnalystStack.workspace import active_task_dir, find_workspace_root

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_BLOCKED = 2
PREVIEW_ROWS = 20


def error(message: str) -> None:
    """Prints an error line to stderr."""
    print(f"ERROR: {message}", file=sys.stderr)


def guarded(handler: Callable[..., None]) -> Callable[..., None]:
    """Wraps a command handler so failures become messages and exit codes, not tracebacks."""

    @functools.wraps(handler)
    def wrapper(args) -> None:
        try:
            handler(args)
        except SystemExit:
            raise
        except (PathPolicyError, ReadOnlyViolationError) as exc:
            error(f"blocked: {exc}")
            sys.exit(EXIT_BLOCKED)
        except ConnectionError as exc:
            # Driver text can name the host, port, database or user taken from .env files.
            detail = f": {exc}" if os.environ.get("ANALYSTSTACK_DEBUG") == "1" else ""
            if "load plugin" in str(exc) or "No module named" in str(exc):
                # A missing driver is not sensitive and is the most common cause, so say so.
                error(f"the database driver for this connection type is not installed (install its extra){detail}")
            else:
                error(f"could not connect (details withheld so connection settings are not echoed){detail}")
            sys.exit(EXIT_FAIL)
        except DataPackageError as exc:
            error(str(exc))
            sys.exit(EXIT_FAIL)
        except Exception as exc:  # noqa: BLE001 - never echo unexpected driver text
            detail = f": {exc}" if os.environ.get("ANALYSTSTACK_DEBUG") == "1" else ""
            error(f"unexpected failure ({type(exc).__name__}){detail}")
            sys.exit(EXIT_FAIL)
        finally:
            close_all_connections()

    return wrapper


def _used_range_end(path: Path, sheet: str | int) -> str | None:
    """Returns the bottom-right cell of a sheet's used range, e.g. ``"F100"``."""
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[sheet] if isinstance(sheet, int) else workbook[sheet]
        if not worksheet.max_row or not worksheet.max_column:
            return None
        return f"{get_column_letter(worksheet.max_column)}{worksheet.max_row}"
    finally:
        workbook.close()


def read_frame(
    path: str, sheet: str | int | None = None, start_cell: str = "A1", end_cell: str | None = None
) -> pd.DataFrame:
    """Reads a CSV, Excel or Parquet file after applying the read policy.

    Raises:
        AnalystStack.exceptions.errors.PathPolicyError: If the path is refused.
        AnalystStack.exceptions.errors.ValidationError: If the file type is not supported.
    """
    from AnalystStack.io import io

    target = check_read(path)
    suffix = target.suffix.lower()
    if suffix in (".csv", ".txt"):
        return io.read.csv(str(target))
    if suffix in (".xlsx", ".xlsm"):
        sheet_name = 0 if sheet is None else sheet
        # With no end cell, DataReader.excel spans every possible Excel column, which pandas
        # rejects as out of bounds; bound the read to the sheet's real extent instead.
        end_cell = end_cell or _used_range_end(target, sheet_name)
        return io.read.excel(str(target), sheet_name=sheet_name, start_cell=start_cell, end_cell=end_cell)
    if suffix == ".parquet":
        return io.read.parquet(str(target))
    raise ValidationError(f"Unsupported input type {suffix!r}; use .csv, .xlsx or .parquet.")


def write_frame(df: pd.DataFrame, path: str, sheet: str = "Data") -> Path:
    """Writes a DataFrame to CSV, Excel, Parquet, Markdown or text after applying the write policy.

    Raises:
        AnalystStack.exceptions.errors.PathPolicyError: If the path is refused.
        AnalystStack.exceptions.errors.ValidationError: If the file type is not supported.
    """
    target = check_write(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.lower()
    if suffix == ".csv":
        df.to_csv(target, index=False)
    elif suffix == ".xlsx":
        df.to_excel(target, sheet_name=sheet[:31], index=False)
    elif suffix == ".parquet":
        df.to_parquet(target, index=False)
    elif suffix in (".md", ".txt"):
        target.write_text(df.to_markdown(index=False) + "\n", encoding="utf-8")
    else:
        raise ValidationError(f"Unsupported output type {suffix!r}; use .csv, .xlsx, .parquet, .md or .txt.")
    return target


def show_frame(df: pd.DataFrame, rows: int = PREVIEW_ROWS) -> None:
    """Prints the shape and a Markdown preview of the first rows."""
    print(f"rows={len(df)} columns={len(df.columns)}")
    if len(df.columns):
        print(df.head(rows).to_markdown(index=False))
        if len(df) > rows:
            print(f"... {len(df) - rows} more rows (use --out to save the full result)")


def split_csv(value: str | None) -> list[str] | None:
    """Splits ``a,b,c`` into a list, or returns ``None`` for an empty value."""
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def default_scope() -> Path:
    """The folder that decides which config and env levels apply: the active task, else the cwd."""
    root = find_workspace_root()
    if root is not None:
        task = active_task_dir(root)
        if task is not None:
            return task
    return Path.cwd()
