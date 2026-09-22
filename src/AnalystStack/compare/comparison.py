"""Key-by-key comparison of two DataFrames: schema drift, unmatched rows, and value diffs."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class ComparisonResult:
    """The outcome of comparing two DataFrames on a shared key.

    Returned by :func:`compare_dataframes`.

    Attributes:
        left_only_columns: Columns present in ``left`` but not ``right`` — schema drift.
        right_only_columns: Columns present in ``right`` but not ``left`` — schema drift.
        common_columns: Columns present in both frames (excluding the key column(s)),
            i.e. the columns actually checked for value differences.
        left_only_rows: Key values present only in ``left`` (i.e. missing from ``right``),
            as a DataFrame of just the key column(s).
        right_only_rows: Key values present only in ``right`` (i.e. missing from ``left``),
            as a DataFrame of just the key column(s).
        value_differences: Long-format table — one row per ``(key, column)`` pair whose
            value differs between the two frames — with columns for the key(s), ``column``,
            ``left_value``, and ``right_value``.
        key_match_rate: Fraction of the union of keys present on both sides (``1.0`` if
            every key in either frame is present in the other).
        row_match_rate: Fraction of matched keys whose rows are fully identical across
            ``common_columns`` (``1.0`` if there are no matched keys to compare).

    Example:
        ```python
        from AnalystStack.compare import compare_dataframes

        result = compare_dataframes(before, after, on="id")

        result.left_only_rows      # rows only in `before`
        result.right_only_rows     # rows only in `after`
        result.value_differences   # one row per (key, column) that differs
        result.key_match_rate      # fraction of keys present in both frames
        result.row_match_rate      # fraction of matched keys with fully identical rows
        result.is_identical        # False if anything above is non-empty
        ```
    """

    left_only_columns: list[str]
    right_only_columns: list[str]
    common_columns: list[str]
    left_only_rows: pd.DataFrame
    right_only_rows: pd.DataFrame
    value_differences: pd.DataFrame
    key_match_rate: float
    row_match_rate: float

    @property
    def is_identical(self) -> bool:
        """True if both DataFrames have identical columns, keys, and values."""
        return (
            not self.left_only_columns
            and not self.right_only_columns
            and self.left_only_rows.empty
            and self.right_only_rows.empty
            and self.value_differences.empty
        )


def compare_dataframes(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str | list[str],
    suffixes: tuple[str, str] = ("_left", "_right"),
) -> ComparisonResult:
    """Compares two DataFrames that share a key, cell by cell.

    Reports schema drift (columns present on only one side), unmatched rows (keys present
    on only one side), and cell-level value differences for every column common to both
    frames.

    Args:
        left: The "before" / baseline DataFrame.
        right: The "after" / candidate DataFrame.
        on: Column(s) that uniquely identify a row in both DataFrames.
        suffixes: Suffixes used internally to disambiguate overlapping column names
            during the merge. You shouldn't normally need to change this.

    Returns:
        A ``ComparisonResult`` describing every difference found.

    Example:
        ```python
        import pandas as pd
        from AnalystStack.compare import compare_dataframes

        before = pd.DataFrame({"id": [1, 2, 3], "price": [10, 20, 30], "name": ["a", "b", "c"]})
        after = pd.DataFrame({"id": [2, 3, 4], "price": [20, 99, 40], "name": ["b", "c", "d"]})

        result = compare_dataframes(before, after, on="id")
        result.value_differences   # id=3, column="price", left_value=30, right_value=99
        ```
    """
    on_cols = [on] if isinstance(on, str) else list(on)

    left_cols = set(left.columns) - set(on_cols)
    right_cols = set(right.columns) - set(on_cols)
    common_cols = sorted(left_cols & right_cols)
    left_only_columns = sorted(left_cols - right_cols)
    right_only_columns = sorted(right_cols - left_cols)

    merged = left.merge(right, on=on_cols, how="outer", suffixes=suffixes, indicator=True)

    left_only_rows = merged.loc[merged["_merge"] == "left_only", on_cols].reset_index(drop=True)
    right_only_rows = merged.loc[merged["_merge"] == "right_only", on_cols].reset_index(drop=True)
    both = merged.loc[merged["_merge"] == "both"].reset_index(drop=True)

    diff_records = []
    row_is_identical = pd.Series(True, index=both.index)
    for col in common_cols:
        left_col, right_col = f"{col}{suffixes[0]}", f"{col}{suffixes[1]}"
        differs = ~(both[left_col] == both[right_col]) & ~(both[left_col].isna() & both[right_col].isna())
        row_is_identical &= ~differs
        if differs.any():
            mismatched = both.loc[differs, on_cols].copy()
            mismatched["column"] = col
            mismatched["left_value"] = both.loc[differs, left_col].values
            mismatched["right_value"] = both.loc[differs, right_col].values
            diff_records.append(mismatched)

    value_differences = (
        pd.concat(diff_records, ignore_index=True)
        if diff_records
        else pd.DataFrame(columns=[*on_cols, "column", "left_value", "right_value"])
    )

    total_keys = len(merged)
    key_match_rate = len(both) / total_keys if total_keys else 1.0
    row_match_rate = row_is_identical.mean() if len(both) else 1.0

    return ComparisonResult(
        left_only_columns=left_only_columns,
        right_only_columns=right_only_columns,
        common_columns=common_cols,
        left_only_rows=left_only_rows,
        right_only_rows=right_only_rows,
        value_differences=value_differences,
        key_match_rate=float(key_match_rate),
        row_match_rate=float(row_match_rate),
    )
