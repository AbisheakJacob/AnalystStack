"""Tests for AnalystStack.report.builder.ReportBuilder."""

import pandas as pd

from AnalystStack.compare import compare_dataframes, summarize
from AnalystStack.report import ReportBuilder
from AnalystStack.validate import Validator, not_null, unique


def test_build_returns_report_with_title_and_timestamp():
    report = ReportBuilder("My Report").build()
    assert report.title == "My Report"
    assert report.generated_at is not None
    assert report.sections == []


def test_add_dataframe_appends_a_section():
    df = pd.DataFrame({"a": [1]})
    report = ReportBuilder().add_dataframe(df, name="Custom", narrative="note").build()

    assert len(report.sections) == 1
    section = report.sections[0]
    assert section.name == "Custom"
    assert section.narrative == "note"
    pd.testing.assert_frame_equal(section.dataframe, df)


def test_add_validation_includes_pass_fail_narrative():
    df = pd.DataFrame({"id": [1, 2, 2], "price": [10.0, None, 20.0]})
    validation_report = Validator([not_null("price"), unique("id")]).validate(df)

    report = ReportBuilder().add_validation(validation_report).build()

    section = report.sections[0]
    assert section.name == "Validation"
    assert section.narrative is not None
    assert "0 of 2 rule(s) passed" in section.narrative
    assert section.dataframe is not None
    assert set(section.dataframe["rule"]) == {"not_null(price)", "unique(id)"}


def test_add_comparison_includes_match_rate_narrative():
    left = pd.DataFrame({"id": [1, 2], "price": [10, 20]})
    right = pd.DataFrame({"id": [1, 2], "price": [10, 99]})
    result = compare_dataframes(left, right, on="id")

    report = ReportBuilder().add_comparison(result).build()

    section = report.sections[0]
    assert section.name == "Comparison"
    assert section.narrative is not None
    assert "Key match rate: 100.0%" in section.narrative
    assert section.dataframe is not None
    assert len(section.dataframe) == 1


def test_add_summary_appends_a_named_section():
    df = pd.DataFrame({"a": [1, 2, 3]})
    summary = summarize(df)

    report = ReportBuilder().add_summary(summary, name="Orders Summary").build()

    assert report.sections[0].name == "Orders Summary"
    pd.testing.assert_frame_equal(report.sections[0].dataframe, summary)


def test_add_table_catalog_and_column_profile_naming():
    tables = pd.DataFrame({"table_name": ["orders"]})
    profile = pd.DataFrame({"column_name": ["id"]})

    report = ReportBuilder().add_table_catalog(tables).add_column_profile(profile, name="orders").build()

    assert report.sections[0].name == "Tables"
    assert report.sections[1].name == "Column Profile: orders"


def test_chaining_preserves_section_order():
    report = (
        ReportBuilder("Chained")
        .add_dataframe(pd.DataFrame({"a": [1]}), name="First")
        .add_dataframe(pd.DataFrame({"a": [2]}), name="Second")
        .build()
    )
    assert [s.name for s in report.sections] == ["First", "Second"]
