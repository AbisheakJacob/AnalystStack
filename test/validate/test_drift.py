"""Tests for AnalystStack.validate.drift."""

import pandas as pd
import pytest

from AnalystStack.exceptions.errors import ConfigurationError
from AnalystStack.validate.drift import compare_dataframe_drift, ks_test, population_stability_index


def test_psi_reports_no_drift_for_identical_distributions():
    baseline = pd.Series(list(range(100)), name="price")
    current = pd.Series(list(range(100)), name="price")

    result = population_stability_index(baseline, current)

    assert result.method == "psi"
    assert result.column == "price"
    assert result.p_value is None
    assert not result.drifted
    assert result.statistic < 0.1


def test_psi_reports_drift_for_shifted_distribution():
    baseline = pd.Series(list(range(100)), name="price")
    current = pd.Series([x + 1000 for x in range(100)], name="price")

    result = population_stability_index(baseline, current)

    assert result.drifted
    assert result.statistic > result.threshold


def test_psi_handles_categorical_columns():
    baseline = pd.Series(["a"] * 50 + ["b"] * 50, name="status")
    current = pd.Series(["a"] * 5 + ["b"] * 95, name="status")

    result = population_stability_index(baseline, current)

    assert result.method == "psi"
    assert result.statistic > 0


def test_psi_handles_constant_baseline():
    # A constant baseline collapses quantile bin edges to a single value -- population_stability_index
    # must fall back to a single manual bin rather than erroring on `pd.cut`.
    baseline = pd.Series([5] * 50, name="price")
    current = pd.Series([5] * 25 + [6] * 25, name="price")

    result = population_stability_index(baseline, current)

    assert result.method == "psi"
    assert result.statistic >= 0


def test_psi_unnamed_series_has_no_column():
    result = population_stability_index(pd.Series([1, 2, 3]), pd.Series([1, 2, 3]))
    assert result.column is None


def test_ks_test_raises_without_scipy(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "scipy.stats", None)

    with pytest.raises(ConfigurationError, match="scipy is required"):
        ks_test(pd.Series([1, 2, 3]), pd.Series([1, 2, 3]))


def test_ks_test_reports_drift_for_shifted_distribution():
    pytest.importorskip("scipy")
    baseline = pd.Series(list(range(100)), name="price")
    current = pd.Series([x + 1000 for x in range(100)], name="price")

    result = ks_test(baseline, current)

    assert result.method == "ks"
    assert result.p_value is not None
    assert result.drifted


def test_compare_dataframe_drift_returns_one_row_per_column():
    baseline = pd.DataFrame({"price": list(range(50)), "status": ["a"] * 50})
    current = pd.DataFrame({"price": list(range(50)), "status": ["a"] * 50, "extra": [1] * 50})

    result = compare_dataframe_drift(baseline, current)

    assert set(result["column"]) == {"price", "status"}
    assert list(result.columns) == ["column", "method", "statistic", "p_value", "threshold", "drifted"]
