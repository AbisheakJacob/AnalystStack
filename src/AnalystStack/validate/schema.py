"""Whole-frame structural validation: column existence, ordering, and dtype checks.

A :class:`~AnalystStack.validate.rules.Rule` reports pass/fail plus which *rows* failed,
which doesn't fit "this column doesn't exist at all" — there's no row to point at. This
module's :class:`SchemaCheckResult` carries that richer detail instead, with
:func:`schema_rule` as an adapter when you want a schema check folded into a
:class:`~AnalystStack.validate.validator.Validator` alongside ordinary per-column rules.
"""

from dataclasses import dataclass, field

import pandas as pd

from AnalystStack.exceptions.errors import ValidationError
from AnalystStack.validate.rules import Rule


@dataclass
class SchemaCheckResult:
    """The outcome of checking a DataFrame's columns against an expected schema.

    Returned by :func:`check_schema`.

    Attributes:
        passed: ``True`` if `missing_columns`, `extra_columns`, and `dtype_mismatches` are
            all empty and `order_mismatch` is ``False``.
        missing_columns: Columns `expected_columns` requires that the DataFrame doesn't
            have.
        extra_columns: Columns the DataFrame has that `expected_columns` doesn't mention.
            Only populated when ``strict=True`` was passed to :func:`check_schema`.
        dtype_mismatches: ``{column: (expected_dtype, actual_dtype)}`` for every column
            present in the DataFrame whose dtype doesn't match what `expected_columns`
            specified. Only populated when `expected_columns` was passed as a ``dict``.
        order_mismatch: ``True`` if ``ordered=True`` was passed to :func:`check_schema` and
            the columns common to both the DataFrame and `expected_columns` don't appear in
            the same relative order in both.
    """

    passed: bool
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    dtype_mismatches: dict[str, tuple[str, str]] = field(default_factory=dict)
    order_mismatch: bool = False


def check_schema(
    df: pd.DataFrame,
    expected_columns: list[str] | dict[str, object],
    *,
    ordered: bool = False,
    strict: bool = False,
) -> SchemaCheckResult:
    """Checks a DataFrame's columns against an expected schema.

    Args:
        df: The DataFrame to check.
        expected_columns: Either a list of required column names, or a ``{column: dtype}``
            mapping to additionally check each column's dtype (anything comparable to a
            pandas dtype, e.g. ``"int64"`` or a numpy/pandas dtype object — see
            :func:`~AnalystStack.validate.rules.has_dtype`).
        ordered: If ``True``, also fail when the columns common to both `df` and
            `expected_columns` aren't in the same relative order (extra/missing columns
            don't count against this — only the relative order of what's shared).
        strict: If ``True``, also fail when `df` has columns `expected_columns` doesn't
            mention (reported in `SchemaCheckResult.extra_columns`).

    Returns:
        A `SchemaCheckResult` describing every mismatch found.

    Example:
        ```python
        from AnalystStack.validate.schema import check_schema

        result = check_schema(df, {"id": "int64", "price": "float64"})
        result.passed             # False
        result.missing_columns    # ["price"] if df has no such column
        ```
    """
    expected_names = list(expected_columns)
    actual_names = list(df.columns)
    actual_set = set(actual_names)
    expected_set = set(expected_names)

    missing_columns = [c for c in expected_names if c not in actual_set]
    extra_columns = [c for c in actual_names if c not in expected_set] if strict else []

    dtype_mismatches: dict[str, tuple[str, str]] = {}
    if isinstance(expected_columns, dict):
        for column, expected_dtype in expected_columns.items():
            if column in actual_set:
                actual_dtype = df[column].dtype
                if actual_dtype != expected_dtype:
                    dtype_mismatches[column] = (str(expected_dtype), str(actual_dtype))

    order_mismatch = False
    if ordered:
        expected_order = [c for c in expected_names if c in actual_set]
        actual_order = [c for c in actual_names if c in expected_set]
        order_mismatch = expected_order != actual_order

    passed = not (missing_columns or extra_columns or dtype_mismatches or order_mismatch)
    return SchemaCheckResult(
        passed=passed,
        missing_columns=missing_columns,
        extra_columns=extra_columns,
        dtype_mismatches=dtype_mismatches,
        order_mismatch=order_mismatch,
    )


def enforce_schema(
    df: pd.DataFrame,
    expected_columns: list[str] | dict[str, object],
    *,
    ordered: bool = False,
    strict: bool = False,
) -> pd.DataFrame:
    """Checks `df` against `expected_columns` and raises if it doesn't match.

    Mirrors :meth:`AnalystStack.validate.validator.Validator.enforce`'s raise-with-details,
    return-unchanged-on-success contract, for schema checks.

    Args:
        df: The DataFrame to check.
        expected_columns: See :func:`check_schema`.
        ordered: See :func:`check_schema`.
        strict: See :func:`check_schema`.

    Returns:
        ``df``, unchanged, if the schema matched.

    Raises:
        AnalystStack.exceptions.errors.ValidationError: If the schema didn't match. The
            message lists every mismatch found.
    """
    result = check_schema(df, expected_columns, ordered=ordered, strict=strict)
    if not result.passed:
        details = []
        if result.missing_columns:
            details.append(f"missing columns: {result.missing_columns}")
        if result.extra_columns:
            details.append(f"unexpected columns: {result.extra_columns}")
        if result.dtype_mismatches:
            details.append(f"dtype mismatches: {result.dtype_mismatches}")
        if result.order_mismatch:
            details.append("columns are not in the expected order")
        raise ValidationError(f"DataFrame failed schema validation: {'; '.join(details)}")
    return df


def schema_rule(
    expected_columns: list[str] | dict[str, object],
    *,
    ordered: bool = False,
    strict: bool = False,
) -> Rule:
    """Wraps :func:`check_schema` as a single pass/fail `Rule`, for `Validator` composition.

    The rule reports pass/fail only (every row is marked the same way, since a schema
    mismatch isn't about specific rows) — call :func:`check_schema` directly instead when you
    need the mismatch detail (missing columns, dtype mismatches, etc).

    Args:
        expected_columns: See :func:`check_schema`.
        ordered: See :func:`check_schema`.
        strict: See :func:`check_schema`.

    Returns:
        A `Rule` named ``"schema"``.

    Example:
        ```python
        from AnalystStack.validate import Validator, not_null
        from AnalystStack.validate.schema import schema_rule

        validator = Validator([schema_rule(["id", "price"]), not_null("price")])
        validator.validate(df)
        ```
    """

    def check(df: pd.DataFrame) -> pd.Series:
        passed = check_schema(df, expected_columns, ordered=ordered, strict=strict).passed
        return pd.Series(passed, index=df.index)

    return Rule("schema", check)
