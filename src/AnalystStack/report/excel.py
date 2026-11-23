"""Branded Excel deliverable: Summary, Data, Notes and Query provenance sheets.

`build_branded_workbook` writes one workbook with four sheets in a fixed order:

* ``Summary``: title, generation date, row and column counts, an optional summary table.
* ``Data``: the analysis table with a styled header row, frozen header and auto-fit widths.
* ``Notes``: free text, one note per row (methodology, caveats, definitions).
* ``Query provenance``: one row per SQL run (file, title, description, connection, time, rows),
  normally read from a task's ``sql/`` folder with `AnalystStack.sqllog.read_provenance`.

Colours and fonts come from a `Theme`. The default is neutral; load a house style from a small
YAML file with `Theme.from_yaml` (keys: ``font_name``, ``title_color``, ``header_fill``,
``header_font_color``, ``band_fill``, ``title_size``).
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from AnalystStack.exceptions.errors import ConfigurationError, ValidationError

_MAX_COLUMN_WIDTH = 60


@dataclass(frozen=True)
class Theme:
    """Colours and fonts for a branded workbook. Colours are six-digit hex without ``#``."""

    font_name: str = "Calibri"
    title_color: str = "1F2937"
    header_fill: str = "374151"
    header_font_color: str = "FFFFFF"
    band_fill: str = "F3F4F6"
    title_size: int = 16

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Theme":
        """Loads a theme from YAML; unknown keys are rejected so typos do not pass silently.

        Raises:
            AnalystStack.exceptions.errors.ConfigurationError: If the file is unreadable, not a
                mapping, or has unknown or malformed keys.
        """
        import yaml

        try:
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Cannot read theme file {path}.") from exc
        if not isinstance(data, dict):
            raise ConfigurationError("A theme file must be a mapping.")
        unknown = set(data) - set(asdict(cls()))
        if unknown:
            raise ConfigurationError(f"Unknown theme keys: {sorted(unknown)}.")
        theme = cls(**data)
        for key in ("title_color", "header_fill", "header_font_color", "band_fill"):
            value = str(getattr(theme, key))
            if len(value) != 6 or any(c not in "0123456789abcdefABCDEF" for c in value):
                raise ConfigurationError(f"Theme key {key} must be a six-digit hex colour.")
        return theme


def _excel_value(value: object) -> object:
    """Converts a pandas value into something openpyxl can store."""
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().replace(tzinfo=None)
    if isinstance(value, (list, dict, tuple, set)):
        return str(value)
    return None if pd.isna(value) else value


def _write_table(sheet, frame: pd.DataFrame, theme: Theme, start_row: int = 1) -> None:
    header_font = Font(name=theme.font_name, bold=True, color=theme.header_font_color)
    header_fill = PatternFill("solid", fgColor=theme.header_fill)
    band_fill = PatternFill("solid", fgColor=theme.band_fill)
    body_font = Font(name=theme.font_name)
    for col, name in enumerate(frame.columns, start=1):
        cell = sheet.cell(row=start_row, column=col, value=str(name))
        cell.font, cell.fill = header_font, header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for offset, row in enumerate(frame.itertuples(index=False), start=1):
        for col, value in enumerate(row, start=1):
            cell = sheet.cell(row=start_row + offset, column=col, value=_excel_value(value))
            cell.font = body_font
            if offset % 2 == 0:
                cell.fill = band_fill
    for col, name in enumerate(frame.columns, start=1):
        longest = max([len(str(name))] + [len(str(v)) for v in frame.iloc[:200, col - 1].tolist()])
        sheet.column_dimensions[get_column_letter(col)].width = min(max(10, longest + 2), _MAX_COLUMN_WIDTH)
    sheet.freeze_panes = sheet.cell(row=start_row + 1, column=1)


def build_branded_workbook(
    path: str | Path,
    data: pd.DataFrame,
    *,
    title: str,
    summary: pd.DataFrame | None = None,
    notes: list[str] | str | None = None,
    provenance: pd.DataFrame | None = None,
    theme: Theme | None = None,
) -> Path:
    """Writes the four-sheet workbook.

    Args:
        path: Output ``.xlsx`` path. An existing file is replaced.
        data: The analysis table for the ``Data`` sheet.
        title: The title shown on the ``Summary`` sheet.
        summary: An optional summary table placed under the headline figures.
        notes: One note, or a list of notes, for the ``Notes`` sheet.
        provenance: The query provenance table; an empty one is written if omitted.
        theme: Colours and fonts; defaults to the neutral `Theme`.

    Returns:
        The path written.

    Raises:
        AnalystStack.exceptions.errors.ValidationError: If the title is empty or the path does
            not end in ``.xlsx``.
    """
    out = Path(path)
    if out.suffix.lower() != ".xlsx":
        raise ValidationError("The output path must end in .xlsx.")
    if not title.strip():
        raise ValidationError("A workbook title is required.")
    theme = theme or Theme()
    notes_list = [notes] if isinstance(notes, str) else list(notes or [])
    provenance = provenance if provenance is not None else pd.DataFrame(columns=["file", "title", "description"])

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    summary_sheet["A1"] = title.strip()
    summary_sheet["A1"].font = Font(name=theme.font_name, bold=True, size=theme.title_size, color=theme.title_color)
    facts = [
        ("Generated", datetime.now().strftime("%Y/%m/%d %H:%M")),
        ("Data rows", len(data)),
        ("Data columns", len(data.columns)),
        ("Queries run", len(provenance)),
    ]
    for index, (label, value) in enumerate(facts, start=3):
        summary_sheet.cell(row=index, column=1, value=label).font = Font(name=theme.font_name, bold=True)
        summary_sheet.cell(row=index, column=2, value=value).font = Font(name=theme.font_name)
    summary_sheet.column_dimensions["A"].width = 18
    summary_sheet.column_dimensions["B"].width = 24
    if summary is not None and not summary.empty:
        _write_table(summary_sheet, summary, theme, start_row=len(facts) + 5)
        summary_sheet.freeze_panes = None

    _write_table(workbook.create_sheet("Data"), data, theme)

    notes_sheet = workbook.create_sheet("Notes")
    notes_sheet["A1"] = "Notes"
    notes_sheet["A1"].font = Font(name=theme.font_name, bold=True, size=theme.title_size - 2, color=theme.title_color)
    for row, text in enumerate(notes_list, start=3):
        cell = notes_sheet.cell(row=row, column=1, value=text)
        cell.font = Font(name=theme.font_name)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    notes_sheet.column_dimensions["A"].width = 100

    _write_table(workbook.create_sheet("Query provenance"), provenance, theme)

    out.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(out)
    workbook.close()
    return out
