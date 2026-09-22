import os
from typing import Any, cast

import pandas as pd
from openpyxl import load_workbook

from AnalystStack.io.utils import parse_excel_cell
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class DataWriter:
    """Handles exporting DataFrames and text to various formats securely.

    Wraps writing to Excel, CSV, Markdown, plain text, and the OS clipboard
    behind a consistent interface. Accessible as the ``write`` attribute of the
    pre-instantiated `AnalystStack.io.io` facade (``io.write.csv(...)``), but can
    also be instantiated directly.
    """

    def excel(
        self,
        df: pd.DataFrame,
        file_path: str,
        sheet_name: str = "Sheet1",
        start_cell: str = "A1",
        # clear_range: Optional[str] = None,
        index: bool = False,
        header: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Writes a DataFrame to Excel. Can target specific cells and safely overlay
        data without destroying the rest of the sheet.

        This method targets an EXISTING workbook: the file is opened with
        `openpyxl`, so ``file_path`` must already point at a real workbook before
        calling this method — it will not create a new file. The target
        ``sheet_name`` is recreated and its contents replaced, but every other
        sheet in the workbook is left intact.

        Args:
            df: The DataFrame to write.
            file_path: Path to an existing Excel workbook.
            sheet_name: Sheet to write into. Its existing contents are replaced;
                other sheets in the workbook are left untouched.
            start_cell: Top-left cell at which to start writing, e.g. ``"A1"``.
            index: If True, writes the DataFrame's index as a column.
            header: If True (default), writes column headers.
            **kwargs: Forwarded to `DataFrame.to_excel`.

        Returns:
            None.

        Raises:
            FileNotFoundError: If ``file_path`` does not point to an existing
                workbook.
            KeyError: If ``sheet_name`` does not exist in the workbook.

        Example:
            ```python
            io.write.excel(df, "report.xlsx", sheet_name="Data", start_cell="B2")
            ```
        """
        start_row, start_col, _ = parse_excel_cell(start_cell)

        # 1. Clear specific cells if requested and file exists
        wb = load_workbook(file_path)
        ws = wb[sheet_name]
        # Delete everything below row 1
        # ws.delete_rows(2, ws.max_row)
        wb.remove(ws)
        ws = wb.create_sheet(sheet_name)

        # Save after clearing
        wb.save(file_path)
        wb.close()

        # 2. Write the DataFrame (Overlay mode preserves existing formatting/data outside our target)
        mode = "a" if os.path.exists(file_path) else "w"
        if_exists = "overlay" if mode == "a" else None

        with pd.ExcelWriter(file_path, engine="openpyxl", mode=mode, if_sheet_exists=if_exists) as writer:
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                startrow=start_row,
                startcol=start_col,
                index=index,
                header=header,
                **kwargs,
            )
        logger.info(f"Successfully wrote data to {file_path} at {start_cell}.")

    def csv(self, df: pd.DataFrame, file_path: str, mode: str = "overwrite", index: bool = False) -> None:
        """Writes to CSV. Prevents duplicating the header row when appending.

        The header row is written when overwriting, or when appending to a file
        that doesn't exist yet; it is omitted when appending to a file that
        already exists, so repeated calls with ``mode="append"`` don't duplicate
        the header row.

        Args:
            df: The DataFrame to write.
            file_path: Path to the CSV file to write.
            mode: Either ``"overwrite"`` (default) to replace the file, or
                ``"append"`` to add rows to the end of an existing file without
                repeating the header row.
            index: If True, writes the DataFrame's index as a column.

        Returns:
            None.

        Example:
            ```python
            io.write.csv(df, "out.csv", mode="append")  # header written only once
            ```
        """
        write_mode = "a" if mode == "append" else "w"

        # Only write the header if we are overwriting, OR if the file doesn't exist yet
        write_header = bool(write_mode == "w" or not os.path.exists(file_path))

        df.to_csv(file_path, mode=write_mode, index=index, header=write_header)
        logger.info(f"Data {'appended' if write_mode == 'a' else 'written'} to {file_path}.")

    def _format_data(self, data: pd.DataFrame | Any, markdown: bool = False) -> str:
        """Internal helper to convert DF to string/markdown, or leave raw text as string."""
        if isinstance(data, pd.DataFrame):
            return cast(str, data.to_markdown(index=False) if markdown else data.to_string(index=False))
        return str(data)

    def markdown(self, data: pd.DataFrame | str, file_path: str, mode: str = "overwrite") -> None:
        """Writes a DataFrame or raw text to a Markdown file.

        A DataFrame is rendered as a Markdown table (via `DataFrame.to_markdown`);
        any other value is converted with `str()` and written as-is. Two trailing
        newlines are appended after the content.

        Args:
            data: The DataFrame or string to write.
            file_path: Path to the Markdown file to write.
            mode: Either ``"overwrite"`` (default) to replace the file, or
                ``"append"`` to add to the end of an existing file.

        Returns:
            None.

        Example:
            ```python
            io.write.markdown(df, "summary.md")  # DataFrame -> Markdown table
            ```
        """
        write_mode = "a" if mode == "append" else "w"
        text_data = self._format_data(data, markdown=True)

        with open(file_path, write_mode, encoding="utf-8") as f:
            f.write(text_data + "\n\n")
        logger.info(f"Markdown written to {file_path}.")

    def txt(self, data: pd.DataFrame | str, file_path: str, mode: str = "overwrite") -> None:
        """Writes a DataFrame or raw text to a standard TXT file.

        A DataFrame is rendered with `DataFrame.to_string`; any other value is
        converted with `str()` and written as-is. A single trailing newline is
        appended after the content.

        Args:
            data: The DataFrame or string to write.
            file_path: Path to the text file to write.
            mode: Either ``"overwrite"`` (default) to replace the file, or
                ``"append"`` to add to the end of an existing file.

        Returns:
            None.

        Example:
            ```python
            io.write.txt("Run completed", "log.txt", mode="append")
            ```
        """
        write_mode = "a" if mode == "append" else "w"
        text_data = self._format_data(data, markdown=False)

        with open(file_path, write_mode, encoding="utf-8") as f:
            f.write(text_data + "\n")
        logger.info(f"Text written to {file_path}.")

    def clipboard(self, data: pd.DataFrame | str) -> None:
        """Copies a DataFrame or string directly to the OS clipboard.

        A DataFrame is copied via `DataFrame.to_clipboard` without its index,
        ready to paste straight into a spreadsheet. Any other value is converted
        to a string and copied the same way, by wrapping it in a single-column,
        single-row, headerless DataFrame.

        Args:
            data: The DataFrame or string to copy.

        Returns:
            None.

        Example:
            ```python
            io.write.clipboard(df)  # paste straight into a sheet
            ```
        """
        if isinstance(data, pd.DataFrame):
            data.to_clipboard(index=False)
        else:
            # Pandas allows us to hijack its clipboard function for plain strings too
            pd.DataFrame([str(data)]).to_clipboard(index=False, header=False)
        logger.info("Data copied to clipboard.")
