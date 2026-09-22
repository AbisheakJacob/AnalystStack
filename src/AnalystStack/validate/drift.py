"""Statistical drift detection between two snapshots of the same column(s).

Pairs naturally with :mod:`AnalystStack.compare`: where `compare_dataframes` diffs two
frames cell-by-cell on a shared key, this module answers a different question — has a
column's *distribution* shifted between a baseline and a current snapshot, even if no
individual row can be matched between them (e.g. two independent samples, or the same table
pulled a month apart).

:func:`population_stability_index` (PSI) is the default method: pure pandas/numpy, no extra
dependency. :func:`ks_test` is more statistically rigorous for numeric columns but requires
``scipy`` (``pip install "AnalystStack[stats]"``), lazy-imported only when called.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from AnalystStack.exceptions.errors import ConfigurationError

_EPSILON = 1e-6


@dataclass
class DriftResult:
    """The outcome of a single drift check between a baseline and current column.

    Attributes:
        column: The column's name, or ``None`` if the input ``Series`` wasn't named.
        method: Which method produced this result: ``"psi"`` or ``"ks"``.
        statistic: The PSI value or the KS test's D-statistic.
        p_value: The KS test's p-value, or ``None`` for PSI (which has no p-value).
        threshold: The `threshold` (PSI) or `alpha` (KS) passed in, echoed back for
            reference.
        drifted: ``True`` if the column is flagged as having drifted -- ``statistic >
            threshold`` for PSI, ``p_value < threshold`` for KS.
    """

    column: str | None
    method: Literal["psi", "ks"]
    statistic: float
    p_value: float | None
    threshold: float
    drifted: bool


def population_stability_index(
    baseline: pd.Series, current: pd.Series, bins: int = 10, threshold: float = 0.25
) -> DriftResult:
    """Computes the Population Stability Index (PSI) between two snapshots of a column.

    Numeric columns are bucketed into `bins` quantile-based bins computed from `baseline`;
    non-numeric columns are compared category by category. Conventional interpretation:
    PSI < 0.1 is stable, 0.1-0.25 is a moderate shift worth a look, and > 0.25 (the default
    `threshold`) is a significant shift.

    Args:
        baseline: The "before" snapshot of the column.
        current: The "after" snapshot of the column, compared against `baseline`'s bins/
            categories.
        bins: Number of quantile bins to use for a numeric column. Ignored for non-numeric
            columns, which use their observed categories instead.
        threshold: The PSI value above which `drifted` is ``True``.

    Returns:
        A `DriftResult` with ``method="psi"`` and ``p_value=None``.

    Example:
        ```python
        from AnalystStack.validate.drift import population_stability_index

        result = population_stability_index(orders_last_month["price"], orders_this_month["price"])
        result.drifted  # True if price distribution shifted significantly
        ```
    """
    baseline_clean = baseline.dropna()
    current_clean = current.dropna()

    if pd.api.types.is_numeric_dtype(baseline_clean):
        edges = np.unique(np.nanquantile(baseline_clean, np.linspace(0, 1, bins + 1)))
        if len(edges) < 2:
            edges = np.array([baseline_clean.min() - _EPSILON, baseline_clean.max() + _EPSILON])
        baseline_counts = pd.cut(baseline_clean, bins=edges, include_lowest=True).value_counts(sort=False)
        current_counts = pd.cut(current_clean, bins=edges, include_lowest=True).value_counts(sort=False)
    else:
        categories = pd.Index(baseline_clean.unique()).union(current_clean.unique())
        baseline_counts = baseline_clean.value_counts().reindex(categories, fill_value=0)
        current_counts = current_clean.value_counts().reindex(categories, fill_value=0)

    baseline_pct = (baseline_counts / max(len(baseline_clean), 1)).clip(lower=_EPSILON)
    current_pct = (current_counts / max(len(current_clean), 1)).clip(lower=_EPSILON)

    psi = float(((current_pct - baseline_pct) * np.log(current_pct / baseline_pct)).sum())

    return DriftResult(
        column=baseline.name if isinstance(baseline.name, str) else None,
        method="psi",
        statistic=psi,
        p_value=None,
        threshold=threshold,
        drifted=psi > threshold,
    )


def ks_test(baseline: pd.Series, current: pd.Series, alpha: float = 0.05) -> DriftResult:
    """Runs a two-sample Kolmogorov-Smirnov test between two snapshots of a numeric column.

    Requires ``scipy`` (``pip install "AnalystStack[stats]"``), imported only inside this
    function -- `AnalystStack.validate` never requires it just to be imported.

    Args:
        baseline: The "before" snapshot of the column.
        current: The "after" snapshot of the column.
        alpha: The significance level below which `drifted` is ``True``.

    Returns:
        A `DriftResult` with ``method="ks"``, ``statistic`` set to the KS test's
        D-statistic, and `p_value` set.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If ``scipy`` isn't installed.

    Example:
        ```python
        from AnalystStack.validate.drift import ks_test

        result = ks_test(orders_last_month["price"], orders_this_month["price"])
        ```
    """
    try:
        from scipy.stats import ks_2samp
    except ImportError as e:
        raise ConfigurationError(
            "scipy is required for KS-test drift detection; install with pip install 'AnalystStack[stats]'"
        ) from e

    statistic, p_value = ks_2samp(baseline.dropna(), current.dropna())
    return DriftResult(
        column=baseline.name if isinstance(baseline.name, str) else None,
        method="ks",
        statistic=float(statistic),
        p_value=float(p_value),
        threshold=alpha,
        drifted=bool(p_value < alpha),
    )


def compare_dataframe_drift(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    columns: list[str] | None = None,
    method: Literal["psi", "ks"] = "psi",
) -> pd.DataFrame:
    """Checks drift across every shared column of two DataFrames in one call.

    The primary entry point most callers use -- `population_stability_index`/`ks_test` are
    the lower-level single-column primitives this is built on.

    Args:
        baseline: The "before" snapshot.
        current: The "after" snapshot, compared column by column against `baseline`.
        columns: Which columns to check. Defaults to every column present in both frames.
        method: ``"psi"`` (default, pure pandas/numpy) or ``"ks"`` (requires ``scipy``, and
            only really meaningful for numeric columns).

    Returns:
        A tidy DataFrame with one row per column checked and columns ``column``, ``method``,
        ``statistic``, ``p_value``, ``threshold``, and ``drifted`` -- mirroring
        `AnalystStack.compare.summarize`'s one-row-per-column shape.

    Example:
        ```python
        from AnalystStack.validate.drift import compare_dataframe_drift

        drift_report = compare_dataframe_drift(orders_last_month, orders_this_month)
        drift_report[drift_report["drifted"]]  # columns that shifted
        ```
    """
    check = ks_test if method == "ks" else population_stability_index
    target_columns = columns if columns is not None else [c for c in baseline.columns if c in current.columns]

    rows = []
    for col in target_columns:
        result = check(baseline[col], current[col])
        rows.append(
            {
                "column": col,
                "method": result.method,
                "statistic": result.statistic,
                "p_value": result.p_value,
                "threshold": result.threshold,
                "drifted": result.drifted,
            }
        )
    return pd.DataFrame(rows, columns=["column", "method", "statistic", "p_value", "threshold", "drifted"])
