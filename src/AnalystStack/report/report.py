"""The `DataQualityReport`/`ReportSection` result types and their file-writing logic."""

import os
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd
from openpyxl import Workbook, load_workbook

from AnalystStack.io import io
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)

_EXCEL_SHEET_NAME_LIMIT = 31  # Excel's own hard limit on sheet name length.


@dataclass
class ReportSection:
    """One section of a `DataQualityReport`.

    Attributes:
        name: The section's heading (in markdown/text output) and sheet name (in Excel
            output, truncated to Excel's 31-character sheet-name limit).
        dataframe: The section's tabular content. ``None`` for a narrative-only section.
        narrative: A short line of prose shown above `dataframe` (or standalone if
            `dataframe` is ``None``).
    """

    name: str
    dataframe: pd.DataFrame | None = None
    narrative: str | None = None


@dataclass
class DataQualityReport:
    """A titled, ordered collection of `ReportSection`\\ s, ready to write to a file.

    Build one with `AnalystStack.report.builder.ReportBuilder` rather than constructing this
    directly.

    Attributes:
        title: The report's title, shown as a top-level heading.
        generated_at: When the report was built.
        sections: The report's sections, in display order.
    """

    title: str
    generated_at: pd.Timestamp
    sections: list[ReportSection] = field(default_factory=list)

    def write(self, file_path: str, format: Literal["markdown", "excel", "txt"] = "markdown") -> None:
        """Writes this report to a file, entirely through `AnalystStack.io.io.write`.

        No new file-writing logic is introduced beyond what's needed to satisfy
        `AnalystStack.io.writer.DataWriter.excel`'s precondition that its target sheet
        already exist (see `_write_excel`) -- every actual byte written goes through the
        existing `io.write.markdown`/`txt`/`excel` methods.

        Args:
            file_path: Path to write the report to.
            format: ``"markdown"`` (default), ``"excel"``, or ``"txt"``.

        Raises:
            ValueError: If `format` isn't one of the three supported values.

        Example:
            ```python
            report.write("orders_report.md")
            report.write("orders_report.xlsx", format="excel")
            ```
        """
        if format == "markdown":
            self._write_text(io.write.markdown, file_path, markdown=True)
        elif format == "txt":
            self._write_text(io.write.txt, file_path, markdown=False)
        elif format == "excel":
            self._write_excel(file_path)
        else:
            raise ValueError(f"Unsupported format: {format!r}. Expected 'markdown', 'excel', or 'txt'.")
        logger.info(f"Report '{self.title}' written to {file_path} ({format}).")

    def _write_text(self, write_fn, file_path: str, markdown: bool) -> None:
        """Shared body for the markdown/txt formats, which differ only in which
        `AnalystStack.io.writer.DataWriter` method renders each piece and whether headings
        get a leading ``#``/``##``."""
        title_heading = f"# {self.title}" if markdown else self.title
        section_heading = "## {}" if markdown else "{}"

        write_fn(title_heading, file_path, mode="overwrite")
        write_fn(f"Generated {self.generated_at:%Y-%m-%d %H:%M} UTC", file_path, mode="append")

        for section in self.sections:
            write_fn(section_heading.format(section.name), file_path, mode="append")
            if section.narrative:
                write_fn(section.narrative, file_path, mode="append")
            if section.dataframe is not None:
                write_fn(section.dataframe, file_path, mode="append")

    def _write_excel(self, file_path: str) -> None:
        """Writes one sheet per section that carries a DataFrame.

        `io.write.excel` requires its target sheet to already exist in the workbook (see
        its docstring) -- this method's only job is satisfying that precondition, by
        creating an empty workbook (if `file_path` doesn't exist yet) with every section's
        sheet pre-created, before delegating the actual write of each section to
        `io.write.excel`.
        """
        sections_with_data = [s for s in self.sections if s.dataframe is not None]
        sheet_names = [s.name[:_EXCEL_SHEET_NAME_LIMIT] for s in sections_with_data]

        workbook = load_workbook(file_path) if os.path.exists(file_path) else Workbook()
        if "Sheet" in workbook.sheetnames and workbook["Sheet"].max_row == 1 and workbook["Sheet"].max_column == 1:
            # Only the default, still-empty sheet a fresh Workbook() ships with -- discard it.
            workbook.remove(workbook["Sheet"])
        for sheet_name in sheet_names:
            if sheet_name not in workbook.sheetnames:
                workbook.create_sheet(sheet_name)
        workbook.save(file_path)
        workbook.close()

        for section, sheet_name in zip(sections_with_data, sheet_names, strict=True):
            io.write.excel(section.dataframe, file_path, sheet_name=sheet_name)
