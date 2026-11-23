"""``analyststack data``: reshape, compare, summarise and validate files.

Validation rules are declared in a YAML file as a list of built-in rules. ``custom()`` rules
are Python closures and are deliberately not available here (serialising arbitrary code is
unsafe); use the Python API for those::

    - rule: not_null
      column: store_id
    - rule: in_range
      column: units
      min_value: 0
    - rule: is_fresh
      column: syncstartdatetime
      max_age_hours: 24
"""

import argparse
import sys

import pandas as pd

from AnalystStack.commands._common import EXIT_FAIL, guarded, read_frame, show_frame, split_csv, write_frame
from AnalystStack.exceptions.errors import ValidationError
from AnalystStack.paths import check_read


@guarded
def handle_tidy(args: argparse.Namespace) -> None:
    """Reshapes a wide file into tidy (long) format."""
    from AnalystStack.tidy import to_tidy

    frame = read_frame(args.input, args.sheet)
    result = to_tidy(
        frame,
        id_vars=split_csv(args.id_vars) or [],
        value_vars=split_csv(args.value_vars),
        var_name=args.var_name,
        value_name=args.value_name,
        dropna=not args.keep_na,
    )
    print(f"rows={len(result)} columns={len(result.columns)}")
    print(f"wrote: {write_frame(result, args.output)}")


@guarded
def handle_untidy(args: argparse.Namespace) -> None:
    """Reshapes a tidy (long) file back into wide format."""
    from AnalystStack.tidy import from_tidy

    frame = read_frame(args.input, args.sheet)
    result = from_tidy(
        frame, index=split_csv(args.index) or [], columns=args.columns, values=args.values, aggfunc=args.aggfunc
    )
    print(f"rows={len(result)} columns={len(result.columns)}")
    print(f"wrote: {write_frame(result, args.output)}")


@guarded
def handle_compare(args: argparse.Namespace) -> None:
    """Compares two files on a key; exits 1 if they differ."""
    from AnalystStack.compare import compare_dataframes

    left, right = read_frame(args.left), read_frame(args.right)
    keys = split_csv(args.on) or []
    result = compare_dataframes(left, right, on=keys if len(keys) > 1 else keys[0])
    print(f"left_only_columns={result.left_only_columns}")
    print(f"right_only_columns={result.right_only_columns}")
    print(f"left_only_rows={len(result.left_only_rows)} right_only_rows={len(result.right_only_rows)}")
    print(f"value_differences={len(result.value_differences)}")
    print(f"key_match_rate={result.key_match_rate:.4f} row_match_rate={result.row_match_rate:.4f}")
    if args.out:
        print(f"wrote: {write_frame(result.value_differences, args.out)}")
    if not result.is_identical:
        sys.exit(EXIT_FAIL)
    print("IDENTICAL")


@guarded
def handle_summarize(args: argparse.Namespace) -> None:
    """Profiles a file in one call."""
    from AnalystStack.compare import summarize

    summary = summarize(read_frame(args.input, args.sheet))
    show_frame(summary, rows=200)
    if args.out:
        print(f"wrote: {write_frame(summary, args.out)}")


def _build_rule(spec: dict):
    from AnalystStack import validate as v

    spec = dict(spec)
    name = spec.pop("rule", None)
    if name == "is_fresh":
        hours = spec.pop("max_age_hours", None)
        if hours is None:
            raise ValidationError("is_fresh needs max_age_hours.")
        spec["max_age"] = pd.Timedelta(hours=float(hours))
    factories = {
        n: getattr(v, n)
        for n in (
            "not_null", "unique", "in_range", "is_in", "matches_regex", "has_dtype",
            "row_count_between", "no_duplicate_rows", "is_fresh", "no_outliers",
        )
    }  # fmt: skip
    if name not in factories:
        raise ValidationError(f"Unknown rule {name!r}. Available: {sorted(factories)}.")
    try:
        return factories[name](**spec)
    except TypeError as exc:
        raise ValidationError(f"Rule {name!r} has wrong arguments: {sorted(spec)}.") from exc


@guarded
def handle_validate(args: argparse.Namespace) -> None:
    """Runs declarative rules against a file; exits 1 if any rule fails."""
    import yaml

    from AnalystStack.validate import Validator

    frame = read_frame(args.input, args.sheet)
    try:
        specs = yaml.safe_load(check_read(args.rules).read_text(encoding="utf-8")) or []
    except yaml.YAMLError as exc:
        raise ValidationError("The rules file is not valid YAML.") from exc
    if not isinstance(specs, list) or not all(isinstance(s, dict) for s in specs):
        raise ValidationError("The rules file must be a YAML list of mappings.")
    report = Validator([_build_rule(s) for s in specs]).validate(frame)
    table = report.to_frame()
    show_frame(table, rows=200)
    if args.out:
        print(f"wrote: {write_frame(table, args.out)}")
    if not report.passed:
        print("FAILED")
        sys.exit(EXIT_FAIL)
    print("PASSED")


def add_parser(subparsers) -> None:
    """Registers ``data``."""
    data = subparsers.add_parser("data", help="Reshape, compare, summarise and validate files.")
    sub = data.add_subparsers(dest="data_command", required=True)

    tidy = sub.add_parser("tidy", help="Wide to tidy (long).")
    tidy.add_argument("input")
    tidy.add_argument("output")
    tidy.add_argument("--id-vars", required=True, help="Comma-separated identifier columns.")
    tidy.add_argument("--value-vars", default=None, help="Comma-separated columns to unpivot (default: all others).")
    tidy.add_argument("--var-name", default="variable")
    tidy.add_argument("--value-name", default="value")
    tidy.add_argument("--keep-na", action="store_true", help="Keep rows whose value is empty.")
    tidy.add_argument("--sheet", default=None)
    tidy.set_defaults(func=handle_tidy)

    untidy = sub.add_parser("untidy", help="Tidy (long) back to wide.")
    untidy.add_argument("input")
    untidy.add_argument("output")
    untidy.add_argument("--index", required=True, help="Comma-separated row identifier columns.")
    untidy.add_argument("--columns", required=True, help="Column whose values become the new columns.")
    untidy.add_argument("--values", required=True, help="Column holding the values.")
    untidy.add_argument("--aggfunc", default="first")
    untidy.add_argument("--sheet", default=None)
    untidy.set_defaults(func=handle_untidy)

    compare = sub.add_parser("compare", help="Compare two files on a key; exit 1 if they differ.")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--on", required=True, help="Key column, or comma-separated key columns.")
    compare.add_argument("--out", default=None, help="Write the value differences here.")
    compare.set_defaults(func=handle_compare)

    summarize = sub.add_parser("summarize", help="One-call profile of a file.")
    summarize.add_argument("input")
    summarize.add_argument("--sheet", default=None)
    summarize.add_argument("--out", default=None)
    summarize.set_defaults(func=handle_summarize)

    validate = sub.add_parser("validate", help="Run declarative rules from a YAML file; exit 1 on failure.")
    validate.add_argument("input")
    validate.add_argument("--rules", required=True, help="YAML list of rules.")
    validate.add_argument("--sheet", default=None)
    validate.add_argument("--out", default=None)
    validate.set_defaults(func=handle_validate)
