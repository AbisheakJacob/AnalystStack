"""Assembles other AnalystStack results into a single, ready-to-write report.

Composes `AnalystStack.validate.results.ValidationReport`,
`AnalystStack.compare.comparison.ComparisonResult`/`AnalystStack.compare.summary.summarize`
output, and connector metadata (``list_tables``/``profile_columns``) into one deliverable —
no scheduling, no orchestration, just one call. Every byte written goes through
`AnalystStack.io.io.write` (markdown, Excel, or plain text); this module adds no new
file-writing logic beyond what's needed to satisfy `DataWriter.excel`'s precondition that
its target sheet already exist.

Build a report with `ReportBuilder`, then call `DataQualityReport.write`.

Example:
    ```python
    from AnalystStack.report import ReportBuilder
    from AnalystStack.validate import Validator, not_null, unique

    report = (
        ReportBuilder("Orders Data Quality Report")
        .add_validation(Validator([not_null("price"), unique("id")]).validate(orders_df))
        .build()
    )
    report.write("orders_report.md")
    ```
"""

from AnalystStack.report.builder import ReportBuilder
from AnalystStack.report.report import DataQualityReport, ReportSection

__all__ = ["ReportBuilder", "DataQualityReport", "ReportSection"]
