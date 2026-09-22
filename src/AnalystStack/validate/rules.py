"""The ``Rule`` type and the factory functions that build the built-in rules.

Each factory below returns a :class:`Rule` bound to one column (:func:`custom` can also
validate across the whole frame). Rules are stateless and reusable — build them once and
pass them to as many :class:`~AnalystStack.validate.validator.Validator` instances as needed.

| Rule | Fails when… |
| ---- | ----------- |
| ``not_null(column)`` | the value is null. |
| ``unique(column)`` | the value is shared with another row. |
| ``in_range(column, min_value=None, max_value=None)`` | the value falls outside the bounds (either bound optional). |
| ``is_in(column, allowed)`` | the value isn't one of ``allowed``. |
| ``matches_regex(column, pattern)`` | the value (as a string) doesn't match ``pattern`` from the start. |
| ``has_dtype(column, dtype)`` | the column's dtype doesn't equal ``dtype`` (a whole-column check). |
| ``row_count_between(min_value=None, max_value=None)`` | the frame's row count is out of bounds. |
| ``no_duplicate_rows(subset=None)`` | the row (or ``subset`` of columns) is shared with another row. |
| ``is_fresh(column, max_age, reference_time=None)`` | the value is older than ``max_age`` before ``reference_time``. |
| ``no_outliers(column, method="iqr", threshold=1.5)`` | the value is an outlier by the IQR or z-score method. |
| ``custom(name, check, column=None)`` | your own ``df -> bool Series`` function returns ``False``. |
"""

import re
from collections.abc import Callable, Iterable
from typing import Literal

import pandas as pd

from AnalystStack.validate.results import CheckResult


class Rule:
    """A single, reusable validation check.

    A ``Rule`` pairs a name with a ``check`` callable that takes the DataFrame being
    validated and returns a boolean ``Series`` aligned to its index (``True`` = passes).
    Build rules with the factory functions in this module (:func:`not_null`, :func:`unique`,
    :func:`in_range`, :func:`is_in`, :func:`matches_regex`, :func:`has_dtype`, :func:`custom`)
    rather than constructing one directly, unless you need a shape the factories don't cover.

    Example:
        ```python
        from AnalystStack.validate import Rule

        rule = Rule("id_is_positive", lambda df: df["id"] > 0, column="id")
        result = rule.evaluate(df)
        ```
    """

    def __init__(self, name: str, check: Callable[[pd.DataFrame], pd.Series], column: str | None = None):
        """Initializes the rule.

        Args:
            name: A short, human-readable identifier shown in reports and error messages.
            check: A function that takes the DataFrame and returns a boolean ``Series``
                (aligned to the DataFrame's index) where ``True`` marks a passing row.
            column: The column this rule targets, if any. Purely informational —
                recorded on the resulting ``CheckResult`` — and left ``None`` for
                whole-frame checks.
        """
        self.name = name
        self.column = column
        self._check = check

    def evaluate(self, df: pd.DataFrame) -> CheckResult:
        """Runs the rule's check against ``df`` and summarizes the outcome.

        Args:
            df: The DataFrame to check.

        Returns:
            A :class:`~AnalystStack.validate.results.CheckResult` describing which rows,
            if any, failed.
        """
        passes = self._check(df)
        failed_indices = df.index[~passes].tolist()
        return CheckResult(
            rule=self.name,
            column=self.column,
            passed=not failed_indices,
            failed_count=len(failed_indices),
            failed_indices=failed_indices,
        )


# --- Rule factories ----------------------------------------------------------------------


def not_null(column: str) -> Rule:
    """Builds a rule that fails any row where ``column`` is null.

    Args:
        column: The column to check.

    Returns:
        A ``Rule`` named ``"not_null(<column>)"``.

    Example:
        ```python
        from AnalystStack.validate import not_null

        not_null("price").evaluate(df)
        ```
    """
    return Rule(f"not_null({column})", lambda df: df[column].notna(), column)


def unique(column: str) -> Rule:
    """Builds a rule that fails every row that shares its ``column`` value with another row.

    Args:
        column: The column to check.

    Returns:
        A ``Rule`` named ``"unique(<column>)"``. Note that both the original and the
        duplicate rows are flagged as failing, not just the second occurrence.
    """
    return Rule(f"unique({column})", lambda df: ~df[column].duplicated(keep=False), column)


def in_range(column: str, min_value: object = None, max_value: object = None) -> Rule:
    """Builds a rule that fails any row where ``column`` falls outside ``[min_value, max_value]``.

    Args:
        column: The column to check.
        min_value: The inclusive lower bound. Omit (``None``) to leave the range
            open-ended below.
        max_value: The inclusive upper bound. Omit (``None``) to leave the range
            open-ended above.

    Returns:
        A ``Rule`` named ``"in_range(<column>)"``. A null value in ``column`` always
        fails, since ``NaN >= min_value`` and ``NaN <= max_value`` are both ``False``.
    """

    def check(df: pd.DataFrame) -> pd.Series:
        passes = pd.Series(True, index=df.index)
        if min_value is not None:
            passes &= df[column] >= min_value
        if max_value is not None:
            passes &= df[column] <= max_value
        return passes

    return Rule(f"in_range({column})", check, column)


def is_in(column: str, allowed: Iterable) -> Rule:
    """Builds a rule that fails any row whose ``column`` value is not one of ``allowed``.

    Args:
        column: The column to check.
        allowed: The set of values a row is allowed to have. Converted to a ``set``
            once at rule-build time, so pass a container of hashable values.

    Returns:
        A ``Rule`` named ``"is_in(<column>)"``.
    """
    allowed_set = set(allowed)
    return Rule(f"is_in({column})", lambda df: df[column].isin(allowed_set), column)


def matches_regex(column: str, pattern: str) -> Rule:
    """Builds a rule that fails any row where ``column`` doesn't match ``pattern``.

    Args:
        column: The column to check.
        pattern: A regular expression. Values are coerced to ``str`` and matched from
            the start of the string via ``re.match`` (not anchored at the end — add a
            trailing ``$`` yourself if you need a full-string match).

    Returns:
        A ``Rule`` named ``"matches_regex(<column>)"``.

    Example:
        ```python
        from AnalystStack.validate import matches_regex

        matches_regex("email", pattern=r"^[^@]+@[^@]+\\.[^@]+$").evaluate(df)
        ```
    """
    compiled = re.compile(pattern)
    return Rule(
        f"matches_regex({column})",
        lambda df: df[column].astype(str).map(lambda value: bool(compiled.match(value))),
        column,
    )


def has_dtype(column: str, dtype: object) -> Rule:
    """Builds a rule that fails every row if ``column``'s dtype doesn't match ``dtype``.

    This is a whole-column check: it compares ``df[column].dtype`` once and, if it
    doesn't equal ``dtype``, marks *every* row of ``df`` as failing (there's no
    per-row notion of dtype).

    Args:
        column: The column to check.
        dtype: The expected dtype — anything comparable to a pandas dtype, e.g.
            ``"int64"``, ``"float64"``, or a numpy/pandas dtype object.

    Returns:
        A ``Rule`` named ``"has_dtype(<column>)"``.
    """
    return Rule(f"has_dtype({column})", lambda df: pd.Series(df[column].dtype == dtype, index=df.index), column)


def row_count_between(min_value: int | None = None, max_value: int | None = None) -> Rule:
    """Builds a rule that fails every row if the frame's total row count is out of bounds.

    This is a whole-frame check, in the same spirit as :func:`has_dtype`: it compares
    ``len(df)`` once and, if it falls outside ``[min_value, max_value]``, marks *every* row
    of ``df`` as failing (there's no per-row notion of "the frame has too many rows").

    Args:
        min_value: The inclusive minimum row count. Omit (``None``) to leave the bound
            open-ended below.
        max_value: The inclusive maximum row count. Omit (``None``) to leave the bound
            open-ended above.

    Returns:
        A ``Rule`` named ``"row_count_between(<min_value>, <max_value>)"``.

    Example:
        ```python
        from AnalystStack.validate import row_count_between

        row_count_between(min_value=1).evaluate(df)  # fails every row if df is empty
        ```
    """

    def check(df: pd.DataFrame) -> pd.Series:
        n = len(df)
        ok = (min_value is None or n >= min_value) and (max_value is None or n <= max_value)
        return pd.Series(ok, index=df.index)

    return Rule(f"row_count_between({min_value}, {max_value})", check)


def no_duplicate_rows(subset: list[str] | None = None) -> Rule:
    """Builds a rule that fails every row that's a duplicate of another, across ``subset``.

    Generalizes :func:`unique` (which only ever considers one column) to a whole row or an
    arbitrary set of columns.

    Args:
        subset: The columns that together must be unique per row. Omit (``None``) to
            require every column to match for two rows to count as duplicates.

    Returns:
        A ``Rule`` named ``"no_duplicate_rows(<subset>)"``. As with :func:`unique`, both the
        original and the duplicate rows are flagged as failing, not just the second
        occurrence.
    """
    label = f"no_duplicate_rows({', '.join(subset)})" if subset else "no_duplicate_rows()"
    return Rule(label, lambda df: ~df.duplicated(subset=subset, keep=False))


def is_fresh(column: str, max_age: pd.Timedelta, reference_time: pd.Timestamp | None = None) -> Rule:
    """Builds a rule that fails any row where ``column`` is older than ``max_age``.

    Args:
        column: The timestamp column to check.
        max_age: The oldest a value is allowed to be, relative to ``reference_time``.
        reference_time: The point in time to measure staleness from. Defaults to ``None``,
            meaning "now" — resolved fresh on every call to ``evaluate()`` (via
            ``pandas.Timestamp.now(tz="UTC")``) rather than once when the rule is built, so
            a rule constructed once and reused across repeated calls stays accurate. Pass an
            explicit value for a reproducible check (e.g. in a test), or to compare against
            a time other than now (e.g. a pipeline run's start time).

    Returns:
        A ``Rule`` named ``"is_fresh(<column>)"``. A null value in ``column`` always fails,
        matching :func:`in_range`'s treatment of nulls. `column` and `reference_time` must
        be timezone-comparable (both naive or both aware) — pandas raises if they aren't.

    Example:
        ```python
        from AnalystStack.validate import is_fresh
        import pandas as pd

        is_fresh("updated_at", max_age=pd.Timedelta(days=1)).evaluate(df)
        ```
    """

    def check(df: pd.DataFrame) -> pd.Series:
        as_of = reference_time if reference_time is not None else pd.Timestamp.now(tz="UTC")
        return (as_of - df[column]) <= max_age

    return Rule(f"is_fresh({column})", check, column)


def no_outliers(column: str, method: Literal["iqr", "zscore"] = "iqr", threshold: float = 1.5) -> Rule:
    """Builds a rule that fails any row where ``column`` is a statistical outlier.

    Args:
        column: The numeric column to check.
        method: ``"iqr"`` (default) flags values outside
            ``[Q1 - threshold * IQR, Q3 + threshold * IQR]``, the classic Tukey fence
            (``threshold=1.5`` is the conventional "mild outlier" cutoff). ``"zscore"``
            flags values more than ``threshold`` standard deviations from the mean.
        threshold: The fence multiplier for ``"iqr"``, or the standard-deviation cutoff for
            ``"zscore"``. Defaults to ``1.5``; a common ``"zscore"`` choice is ``3.0``.

    Returns:
        A ``Rule`` named ``"no_outliers(<column>)"``. A null value in ``column`` always
        fails, matching :func:`in_range`'s treatment of nulls.

    Raises:
        ValueError: If `method` isn't ``"iqr"`` or ``"zscore"``.

    Example:
        ```python
        from AnalystStack.validate import no_outliers

        no_outliers("price", method="zscore", threshold=3.0).evaluate(df)
        ```
    """
    if method not in ("iqr", "zscore"):
        raise ValueError(f"Unknown method: {method!r}. Expected 'iqr' or 'zscore'.")

    def check(df: pd.DataFrame) -> pd.Series:
        series = df[column]
        if method == "iqr":
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            return series.between(q1 - threshold * iqr, q3 + threshold * iqr)
        z_scores = (series - series.mean()) / series.std()
        return z_scores.abs() <= threshold

    return Rule(f"no_outliers({column})", check, column)


def custom(name: str, check: Callable[[pd.DataFrame], pd.Series], column: str | None = None) -> Rule:
    """Wraps an arbitrary DataFrame -> boolean Series function as a ``Rule``.

    Use this for checks the built-in factories don't cover, including whole-frame
    checks that span more than one column.

    Args:
        name: A short, human-readable identifier shown in reports and error messages.
        check: A function that takes the DataFrame and returns a boolean ``Series``
            (aligned to the DataFrame's index) where ``True`` marks a passing row.
        column: The column this rule is about, if it's naturally scoped to one.
            Purely informational; leave ``None`` for whole-frame checks.

    Returns:
        A ``Rule`` wrapping ``check``.

    Example:
        ```python
        from AnalystStack.validate import custom

        custom("price_is_even_id", lambda df: df["id"] % 2 == 0).evaluate(df)
        ```
    """
    return Rule(name, check, column)
