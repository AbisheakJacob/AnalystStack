"""Referential-integrity checks between two DataFrames.

Pairs naturally with :mod:`AnalystStack.compare`: where `compare_dataframes` diffs two
frames that share a key, this module checks a weaker but still common invariant -- every
value in a "child" column must exist somewhere in a "parent" column (e.g. every
``orders.customer_id`` must exist in ``customers.id``), without requiring the two frames to
line up row-for-row.
"""

import pandas as pd

from AnalystStack.validate.results import CheckResult
from AnalystStack.validate.rules import Rule


def check_referential_integrity(
    child: pd.DataFrame,
    child_column: str,
    parent: pd.DataFrame,
    parent_column: str,
    *,
    allow_null: bool = True,
) -> CheckResult:
    """Checks that every value in `child`'s `child_column` exists in `parent`'s `parent_column`.

    Args:
        child: The DataFrame whose column is being checked (the "many" side, e.g. orders).
        child_column: The column in `child` to check.
        parent: The DataFrame supplying the allowed values (the "one" side, e.g.
            customers).
        parent_column: The column in `parent` supplying the allowed values.
        allow_null: If ``True`` (default), a null value in `child_column` passes (an
            optional foreign key). Set ``False`` to require every row to reference a parent.

    Returns:
        A `CheckResult` named ``"referential_integrity(<child_column> -> <parent_column>)"``
        listing every row in `child` whose value doesn't exist in `parent`.

    Example:
        ```python
        from AnalystStack.validate.referential import check_referential_integrity

        result = check_referential_integrity(orders, "customer_id", customers, "id")
        result.passed  # False if any order references a customer_id that doesn't exist
        ```
    """
    values = child[child_column]
    allowed_values = set(parent[parent_column].dropna())
    is_null = values.isna()
    passes = values.isin(allowed_values) | (is_null & allow_null)

    failed_indices = child.index[~passes].tolist()
    return CheckResult(
        rule=f"referential_integrity({child_column} -> {parent_column})",
        column=child_column,
        passed=not failed_indices,
        failed_count=len(failed_indices),
        failed_indices=failed_indices,
    )


def referential_integrity_rule(parent: pd.DataFrame, parent_column: str, child_column: str | None = None) -> Rule:
    """Wraps a referential-integrity check as a `Rule`, for `Validator` composition.

    A null value in `child_column` always passes -- use `check_referential_integrity`
    directly instead if you need to reject nulls too (``allow_null=False``).

    Args:
        parent: The DataFrame supplying the allowed values, captured at rule-build time (a
            snapshot -- later changes to `parent` aren't reflected).
        parent_column: The column in `parent` supplying the allowed values.
        child_column: The column to check when this rule is evaluated against a DataFrame.
            Defaults to `parent_column` (i.e. both frames use the same column name).

    Returns:
        A `Rule` named ``"referential_integrity(<child_column> -> <parent_column>)"``.

    Example:
        ```python
        from AnalystStack.validate import Validator, not_null
        from AnalystStack.validate.referential import referential_integrity_rule

        validator = Validator([
            not_null("customer_id"),
            referential_integrity_rule(customers, "id", child_column="customer_id"),
        ])
        validator.validate(orders)
        ```
    """
    resolved_child_column = child_column or parent_column
    allowed_values = set(parent[parent_column].dropna())

    def check(df: pd.DataFrame) -> pd.Series:
        values = df[resolved_child_column]
        return values.isin(allowed_values) | values.isna()

    return Rule(f"referential_integrity({resolved_child_column} -> {parent_column})", check, resolved_child_column)
