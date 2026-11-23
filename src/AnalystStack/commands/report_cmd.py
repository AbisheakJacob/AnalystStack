"""``analyststack report`` and ``analyststack excel``: markdown and branded Excel deliverables."""

import argparse
from pathlib import Path
from typing import Literal

from AnalystStack.commands._common import default_scope, guarded, read_frame
from AnalystStack.exceptions.errors import ValidationError
from AnalystStack.paths import check_read, check_write
from AnalystStack.workspace import active_task_dir, find_workspace_root


def _name_value(pairs: list[str] | None, flag: str) -> list[tuple[str, str]]:
    parsed = []
    for pair in pairs or []:
        name, sep, value = pair.partition("=")
        if not sep or not name.strip() or not value.strip():
            raise ValidationError(f"{flag} must look like NAME=VALUE, got {pair!r}.")
        parsed.append((name.strip(), value.strip()))
    return parsed


@guarded
def handle_report_build(args: argparse.Namespace) -> None:
    """Builds a markdown, text or Excel report with one section per ``--section NAME=FILE``."""
    from AnalystStack.report import ReportBuilder

    suffix = Path(args.out).suffix.lower()
    formats: dict[str, Literal["markdown", "excel", "txt"]] = {".md": "markdown", ".txt": "txt", ".xlsx": "excel"}
    if suffix not in formats:
        raise ValidationError("The output must end in .md, .txt or .xlsx.")
    narratives = dict(_name_value(args.narrative, "--narrative"))
    builder = ReportBuilder(title=args.title)
    sections = _name_value(args.section, "--section")
    if not sections:
        raise ValidationError("Give at least one --section NAME=FILE.")
    for name, file in sections:
        builder.add_dataframe(read_frame(file), name, narrative=narratives.get(name))
    target = check_write(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    builder.build().write(str(target), format=formats[suffix])
    print(f"wrote: {target}")


@guarded
def handle_excel_build(args: argparse.Namespace) -> None:
    """Builds the four-sheet branded workbook (Summary, Data, Notes, Query provenance)."""
    from AnalystStack.report.excel import Theme, build_branded_workbook
    from AnalystStack.sqllog import read_provenance

    data = read_frame(args.data)
    summary = read_frame(args.summary) if args.summary else None
    notes = list(args.note or [])
    if args.notes_file:
        notes.extend(
            line for line in check_read(args.notes_file).read_text(encoding="utf-8").splitlines() if line.strip()
        )
    task = Path(args.task_dir).resolve() if args.task_dir else _active_or_scope()
    provenance = read_provenance(task)
    theme = Theme.from_yaml(check_read(args.theme)) if args.theme else None
    target = check_write(args.out)
    build_branded_workbook(
        target, data, title=args.title, summary=summary, notes=notes, provenance=provenance, theme=theme
    )
    print(f"wrote: {target} (queries in provenance: {len(provenance)})")


def _active_or_scope() -> Path:
    root = find_workspace_root()
    return (active_task_dir(root) if root is not None else None) or default_scope()


def add_parser(subparsers) -> None:
    """Registers ``report`` and ``excel``."""
    report = subparsers.add_parser("report", help="Build a markdown, text or Excel report from files.")
    rsub = report.add_subparsers(dest="report_command", required=True)
    build = rsub.add_parser("build", help="One section per --section NAME=FILE.")
    build.add_argument("--title", required=True)
    build.add_argument(
        "--section", action="append", metavar="NAME=FILE", help="A section backed by a table file (repeatable)."
    )
    build.add_argument(
        "--narrative", action="append", metavar="NAME=TEXT", help="Text shown above a section (repeatable)."
    )
    build.add_argument("--out", required=True, help="Output .md, .txt or .xlsx.")
    build.set_defaults(func=handle_report_build)

    excel = subparsers.add_parser("excel", help="Branded Excel deliverables.")
    esub = excel.add_subparsers(dest="excel_command", required=True)
    xbuild = esub.add_parser("build", help="Summary, Data, Notes and Query provenance sheets.")
    xbuild.add_argument("--title", required=True)
    xbuild.add_argument("--data", required=True, help="Table for the Data sheet (.csv, .xlsx or .parquet).")
    xbuild.add_argument("--summary", default=None, help="Optional table for the Summary sheet.")
    xbuild.add_argument("--note", action="append", help="A note for the Notes sheet (repeatable).")
    xbuild.add_argument("--notes-file", default=None, help="A text file with one note per line.")
    xbuild.add_argument(
        "--task-dir", default=None, help="Task whose sql/ folder feeds Query provenance (default: active task)."
    )
    xbuild.add_argument("--theme", default=None, help="YAML theme file (fonts and colours).")
    xbuild.add_argument("--out", required=True, help="Output .xlsx path.")
    xbuild.set_defaults(func=handle_excel_build)
