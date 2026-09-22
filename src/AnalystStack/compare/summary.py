"""One-call exploratory-data-analysis profile of a single DataFrame."""

import pandas as pd


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """Profiles every column of ``df`` in one call: dtype, null counts, cardinality, and stats.

    Numeric columns get ``mean`` / ``std`` / ``min`` / ``max``; every other column gets
    ``top_value`` (the most frequent non-null value) instead — the field that doesn't apply
    to a column is left ``None``.

    Args:
        df: The DataFrame to profile.

    Returns:
        A tidy summary DataFrame with one row per column of ``df`` and the columns
        ``column``, ``dtype``, ``count``, ``null_count``, ``null_pct``, ``n_unique``,
        ``mean``, ``std``, ``min``, ``max``, and ``top_value``.

    Example:
        ```python
        from AnalystStack.compare import summarize

        summarize(df)
        #   column  dtype  count  null_count  null_pct  n_unique  mean   std   min   max top_value
        # 0     id  int64      3           0       0.0         3   2.0   1.0   1.0   3.0      None
        # 1  price  int64      3           0       0.0         3  20.0  10.0  10.0  30.0      None
        # 2   name    str      3           0       0.0         3  None  None  None  None         a
        ```
    """
    n = len(df)
    rows = []
    for col in df.columns:
        series = df[col]
        non_null = int(series.notna().sum())
        row = {
            "column": col,
            "dtype": str(series.dtype),
            "count": non_null,
            "null_count": n - non_null,
            "null_pct": round((n - non_null) / n * 100, 2) if n else 0.0,
            "n_unique": int(series.nunique(dropna=True)),
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "top_value": None,
        }
        if pd.api.types.is_numeric_dtype(series):
            row["mean"] = series.mean()
            row["std"] = series.std()
            row["min"] = series.min()
            row["max"] = series.max()
        else:
            mode = series.mode(dropna=True)
            row["top_value"] = mode.iloc[0] if not mode.empty else None
        rows.append(row)

    return pd.DataFrame(rows)
