"""``analyststack io``: render Jinja templates and convert between file formats."""

import argparse

from AnalystStack.commands._common import guarded, read_frame, show_frame, write_frame
from AnalystStack.exceptions.errors import ValidationError
from AnalystStack.paths import check_read, check_write


def _parse_vars(pairs: list[str] | None) -> dict[str, str]:
    context: dict[str, str] = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip():
            raise ValidationError(f"--var must look like name=value, got {key!r}.")
        context[key.strip()] = value
    return context


@guarded
def handle_render(args: argparse.Namespace) -> None:
    """Renders a Jinja template from a file or inline text with ``--var name=value`` variables."""
    from AnalystStack.io import io

    if bool(args.file) == bool(args.text):
        raise ValidationError("Give exactly one of --file or --text.")
    context = _parse_vars(args.var)
    source = str(check_read(args.file)) if args.file else args.text
    rendered = io.read.jinja(source, **context)
    if args.out:
        target = check_write(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered if rendered.endswith("\n") else rendered + "\n", encoding="utf-8")
        print(f"wrote: {target}")
    else:
        print(rendered)


@guarded
def handle_convert(args: argparse.Namespace) -> None:
    """Converts a CSV, Excel or Parquet file into CSV, Excel, Parquet, Markdown or text."""
    frame = read_frame(args.input, args.sheet, args.start_cell, args.end_cell)
    target = write_frame(frame, args.output, sheet=args.sheet if isinstance(args.sheet, str) else "Data")
    print(f"rows={len(frame)} columns={len(frame.columns)}")
    print(f"wrote: {target}")


@guarded
def handle_head(args: argparse.Namespace) -> None:
    """Shows the shape and first rows of a file."""
    show_frame(read_frame(args.input, args.sheet), rows=args.rows)


def add_parser(subparsers) -> None:
    """Registers ``io``."""
    io_parser = subparsers.add_parser("io", help="Render Jinja templates and convert file formats.")
    sub = io_parser.add_subparsers(dest="io_command", required=True)

    render = sub.add_parser("render", help="Render a Jinja template.")
    render.add_argument("--file", default=None, help="Template file.")
    render.add_argument("--text", default=None, help="Inline template text.")
    render.add_argument("--var", action="append", metavar="NAME=VALUE", help="Template variable (repeatable).")
    render.add_argument("--out", default=None, help="Write the result here instead of printing it.")
    render.set_defaults(func=handle_render)

    convert = sub.add_parser("convert", help="Convert between .csv, .xlsx and .parquet (and write .md or .txt).")
    convert.add_argument("input")
    convert.add_argument("output")
    convert.add_argument(
        "--sheet", default=None, help="Excel sheet name to read, and the sheet name written for .xlsx."
    )
    convert.add_argument("--start-cell", default="A1", help="First Excel cell to read.")
    convert.add_argument("--end-cell", default=None, help="Last Excel cell to read.")
    convert.set_defaults(func=handle_convert)

    head = sub.add_parser("head", help="Show the shape and first rows of a file.")
    head.add_argument("input")
    head.add_argument("--sheet", default=None)
    head.add_argument("--rows", type=int, default=20)
    head.set_defaults(func=handle_head)
