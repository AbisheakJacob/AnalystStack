import os
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from AnalystStack.io.utils import parse_excel_cell
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class DataReader:
    """Handles comprehensive data ingestion into DataFrames.

    Wraps `pandas.read_excel`, `pandas.read_csv`, and `pandas.read_parquet` with a
    few convenience behaviors (Excel range selection, header-aware row skipping)
    and adds a `jinja` method for rendering Jinja2 templates (e.g. parameterized
    SQL). Accessible as the ``read`` attribute of the pre-instantiated
    `AnalystStack.io.io` facade (``io.read.csv(...)``), but can also be
    instantiated directly.
    """

    def excel(
        self,
        file_path: str,
        sheet_name: str | int = 0,
        start_cell: str = "A1",
        end_cell: str | None = None,
        has_header: bool = True,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Reads a specific range of an Excel sheet into a DataFrame.

        ``start_cell`` and ``end_cell`` let you grab a sub-range of a sheet
        without loading the whole sheet into memory. When ``end_cell`` is
        omitted, reading continues to the end of the sheet, spanning every
        column from ``start_cell``'s column through the last Excel column
        (``XFD``).

        Args:
            file_path: Path to the ``.xlsx``/``.xls`` workbook to read.
            sheet_name: Sheet name or 0-indexed sheet position to read from.
            start_cell: Top-left cell of the range to read, e.g. ``"A1"``.
            end_cell: Bottom-right cell of the range to read, e.g. ``"F100"``.
                If None (default), reads through to the end of the sheet.
            has_header: If True (default), treats the first row of the range as
                column headers rather than data.
            **kwargs: Forwarded to `pandas.read_excel`.

        Returns:
            A DataFrame containing the requested range.

        Raises:
            Exception: Re-raises whatever `pandas.read_excel` raises (e.g. if the
                file or sheet doesn't exist), after logging the failure.

        Example:
            ```python
            df = io.read.excel(
                "report.xlsx", sheet_name="Data", start_cell="B2", end_cell="F100", has_header=True
            )
            ```
        """
        logger.info(f"Reading Excel: {file_path} (Sheet: {sheet_name})")

        start_row, _, start_col_letter = parse_excel_cell(start_cell)

        usecols = None
        nrows = None

        if end_cell:
            end_row, _, end_col_letter = parse_excel_cell(end_cell)
            usecols = f"{start_col_letter}:{end_col_letter}"
            # Calculate rows to read (accounting for the header if it exists)
            nrows = (end_row - start_row) if has_header else (end_row - start_row + 1)
        else:
            usecols = f"{start_col_letter}:XFD"  # XFD is the max Excel column

        try:
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                skiprows=start_row,
                usecols=usecols,
                nrows=nrows,
                header=0 if has_header else None,
                **kwargs,
            )
            return df
        except Exception as e:
            logger.error(f"Failed to read Excel file: {e}")
            raise

    def csv(
        self, file_path: str, skip_rows: int = 0, delimiter: str = ",", has_header: bool = True, **kwargs: Any
    ) -> pd.DataFrame:
        """Reads a CSV file with advanced parsing options.

        Thin wrapper around `pandas.read_csv` that exposes the most commonly
        tweaked options — row skipping, delimiter, and header presence — directly
        as keyword arguments.

        Args:
            file_path: Path to the CSV file to read.
            skip_rows: Number of rows to skip before parsing begins.
            delimiter: Field delimiter/separator character.
            has_header: If True (default), treats the first parsed row as column
                headers rather than data.
            **kwargs: Forwarded to `pandas.read_csv`.

        Returns:
            A DataFrame containing the parsed CSV contents.

        Example:
            ```python
            df = io.read.csv("data.csv")
            ```
        """
        logger.info(f"Reading CSV: {file_path}")
        return pd.read_csv(file_path, skiprows=skip_rows, sep=delimiter, header=0 if has_header else None, **kwargs)

    def parquet(self, file_path: str, columns: list[str] | None = None, **kwargs: Any) -> pd.DataFrame:
        """Reads Parquet files natively.

        Args:
            file_path: Path to the Parquet file to read.
            columns: Subset of columns to read. If None (default), reads every
                column.
            **kwargs: Forwarded to `pandas.read_parquet`.

        Returns:
            A DataFrame containing the requested Parquet data.

        Example:
            ```python
            df = io.read.parquet("data.parquet")
            ```
        """
        logger.info(f"Reading Parquet: {file_path}")
        return pd.read_parquet(file_path, columns=columns, **kwargs)

    def jinja(self, source: str, **context: Any) -> str:
        """Render a Jinja2 template and return the resulting string.

        ``source`` can be either:

        * a path to a template file, e.g. ``"queries/sales.sql.j2"``, or
        * a raw template string, e.g. ``"SELECT * FROM {{ table }}"``.

        Existing files are loaded from disk (so ``{% include %}`` / ``{% extends %}``
        of sibling templates work); anything else is treated as an inline template
        string. Template variables are supplied as keyword arguments.

        Templates render with `jinja2.StrictUndefined`, so referencing a variable
        you didn't pass raises `jinja2.UndefinedError` instead of silently
        producing an empty string — handy for catching typos in query parameters.
        Autoescaping is off, which is what you want when rendering SQL or other
        plain text (unlike HTML, where autoescaping normally guards against
        injection).

        Args:
            source: Path to a template file or an inline template string.
            **context: Variables made available to the template.

        Returns:
            The rendered template as a string.

        Raises:
            jinja2.UndefinedError: If the template references a variable that was
                not supplied (templates are rendered with ``StrictUndefined``).

        Examples:
            Inline template string:

            ```python
            query = io.read.jinja(
                "SELECT * FROM {{ table }} WHERE dt = '{{ run_date }}'",
                table="sales",
                run_date="2026-05-01",
            )
            ```

            Template file on disk (relative or absolute path):

            ```python
            query = io.read.jinja("queries/monthly_sales.sql.j2", month="2026-05")
            ```
        """
        if os.path.isfile(source):
            path = Path(source)
            logger.info(f"Rendering Jinja template file: {source}")
            env = Environment(
                loader=FileSystemLoader(str(path.parent)),
                undefined=StrictUndefined,
                keep_trailing_newline=True,
                autoescape=False,
            )
            template = env.get_template(path.name)
        else:
            logger.info("Rendering Jinja template from inline string.")
            env = Environment(
                undefined=StrictUndefined,
                keep_trailing_newline=True,
                autoescape=False,
            )
            template = env.from_string(source)

        return template.render(**context)
