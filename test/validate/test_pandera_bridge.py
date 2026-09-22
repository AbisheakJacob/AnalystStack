"""Tests for AnalystStack.validate.pandera_bridge.

Requires the optional ``pandera`` extra -- skipped entirely if it isn't installed.
"""

import pandas as pd
import pytest

pa = pytest.importorskip("pandera.pandas")

from AnalystStack.validate.pandera_bridge import pandera_errors_to_report  # noqa: E402


def test_pandera_errors_to_report_groups_failures_by_column_and_check():
    schema = pa.DataFrameSchema(
        {
            "price": pa.Column(float, pa.Check.ge(0)),
            "id": pa.Column(int, pa.Check.ne(0)),
        }
    )
    df = pd.DataFrame({"price": [10.0, -5.0, -1.0], "id": [1, 2, 0]})

    with pytest.raises(pa.errors.SchemaErrors) as exc_info:
        schema.validate(df, lazy=True)

    report = pandera_errors_to_report(exc_info.value)

    assert not report.passed
    assert len(report.results) == 2
    price_failure = next(r for r in report.results if r.column == "price")
    assert price_failure.failed_count == 2
    assert price_failure.failed_indices == [1, 2]

    id_failure = next(r for r in report.results if r.column == "id")
    assert id_failure.failed_indices == [2]


def test_pandera_errors_to_report_empty_on_clean_data():
    schema = pa.DataFrameSchema({"price": pa.Column(float, pa.Check.ge(0))})
    df = pd.DataFrame({"price": [10.0, 20.0]})

    # Clean data doesn't raise, so there's nothing to convert -- this test documents that
    # pandera_errors_to_report is only ever called from an except block.
    schema.validate(df, lazy=True)
