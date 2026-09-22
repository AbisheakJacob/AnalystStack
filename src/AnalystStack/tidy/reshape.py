"""Reshape DataFrames between tidy (long) and normal (wide) layouts.

The two shapes analysts constantly convert between when preparing data for plotting,
pivoting, or loading into a warehouse: **wide** (one column per variable) and
**tidy / long** (one row per observation).
"""

from collections.abc import Callable

import pandas as pd


def to_tidy(
    df: pd.DataFrame,
    id_vars: str | list[str],
    value_vars: str | list[str] | None = None,
    var_name: str = "variable",
    value_name: str = "value",
    dropna: bool = True,
) -> pd.DataFrame:
    """Reshapes a wide DataFrame into tidy (long) format: one row per observation.

    Use ``value_vars`` to unpivot only a subset of columns; everything not listed in
    ``id_vars`` or ``value_vars`` is left out of the result.

    Args:
        df: The wide-format DataFrame to reshape.
        id_vars: Column(s) that identify each observation and are kept as-is.
        value_vars: Column(s) to unpivot. Defaults to every column not in ``id_vars``.
        var_name: Name of the new column holding the former column labels.
        value_name: Name of the new column holding the former cell values.
        dropna: If True (default), drop rows where ``value_name`` is NaN — a missing
            observation usually isn't a row you want in a tidy table. Pass ``False``
            to keep it.

    Returns:
        A tidy DataFrame with columns ``id_vars + [var_name, value_name]``.

    Example:
        ```python
        import pandas as pd
        from AnalystStack.tidy import to_tidy

        sales = pd.DataFrame({"id": [1, 2], "jan": [10, 20], "feb": [30, None]})
        tidy = to_tidy(sales, id_vars="id", var_name="month", value_name="sales")
        #    id month  sales
        # 0   1   jan   10.0
        # 1   2   jan   20.0
        # 2   1   feb   30.0
        ```
    """
    tidy_df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name=var_name, value_name=value_name)
    if dropna:
        tidy_df = tidy_df.dropna(subset=[value_name]).reset_index(drop=True)
    return tidy_df


def from_tidy(
    df: pd.DataFrame,
    index: str | list[str],
    columns: str,
    values: str,
    aggfunc: str | Callable = "first",
    fill_value: object = None,
) -> pd.DataFrame:
    """Reshapes a tidy (long) DataFrame back into normal (wide) format — the inverse of ``to_tidy``.

    ``from_tidy(to_tidy(df, ...), ...)`` recovers the original wide DataFrame as long as
    no values were dropped along the way — handy for verifying a reshape didn't lose data.

    Args:
        df: The tidy-format DataFrame to reshape.
        index: Column(s) that identify each row of the wide result.
        columns: Column whose distinct values become new wide columns.
        values: Column holding the values to place into the new wide columns.
        aggfunc: Aggregation applied when multiple rows share the same (index, columns)
            pair. Defaults to ``"first"``; pass ``"sum"``, ``"mean"``, or any function
            ``pivot_table`` accepts.
        fill_value: Value used to fill any resulting gaps left by combinations that
            don't exist in the tidy data.

    Returns:
        A wide DataFrame with one row per distinct ``index`` value.

    Example:
        ```python
        from AnalystStack.tidy import from_tidy

        wide = from_tidy(tidy, index="id", columns="month", values="sales")
        #    id   feb   jan
        # 0   1  30.0  10.0
        # 1   2   NaN  20.0
        ```
    """
    wide_df = df.pivot_table(index=index, columns=columns, values=values, aggfunc=aggfunc, fill_value=fill_value)
    wide_df = wide_df.reset_index()
    wide_df.columns.name = None
    return wide_df
