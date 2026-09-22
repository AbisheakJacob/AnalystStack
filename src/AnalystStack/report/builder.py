"""`ReportBuilder`: a chainable builder for assembling a `DataQualityReport`."""

import pandas as pd

from AnalystStack.compare.comparison import ComparisonResult
from AnalystStack.report.report import DataQualityReport, ReportSection
from AnalystStack.validate.results import ValidationReport


class ReportBuilder:
    """Chainable builder that assembles a `DataQualityReport` from other AnalystStack results.

    Each ``add_*`` method returns ``self``, so calls chain the same way
    `AnalystStack.validate.validator.Validator.add` does. There's no scheduling or
    orchestration here -- call :meth:`build` once you've added what you want, then
    `DataQualityReport.write` it to a file.

    Example:
        ```python
        from AnalystStack.report import ReportBuilder
        from AnalystStack.validate import Validator, not_null, unique

        report = (
            ReportBuilder("Orders Data Quality Report")
            .add_table_catalog(bq.list_tables("analytics"))
            .add_column_profile(bq.profile_columns("analytics", "orders"), name="orders")
            .add_validation(Validator([not_null("price"), unique("id")]).validate(orders_df))
            .build()
        )
        report.write("orders_report.md")
        ```
    """

    def __init__(self, title: str = "Data Quality Report"):
        """Initializes the builder.

        Args:
            title: The report's title.
        """
        self.title = title
        self._sections: list[ReportSection] = []

    def add_dataframe(self, df: pd.DataFrame, name: str, narrative: str | None = None) -> "ReportBuilder":
        """Adds an arbitrary DataFrame as a section.

        The escape hatch for anything the other ``add_*`` methods don't cover, e.g.
        `AnalystStack.validate.drift.compare_dataframe_drift`'s output.

        Args:
            df: The DataFrame to include.
            name: The section's heading / sheet name.
            narrative: An optional line of prose shown above the table.

        Returns:
            This builder, for chaining.
        """
        self._sections.append(ReportSection(name=name, dataframe=df, narrative=narrative))
        return self

    def add_validation(self, report: ValidationReport, name: str = "Validation") -> "ReportBuilder":
        """Adds a `ValidationReport` as a section, rendered via `ValidationReport.to_frame`.

        Args:
            report: The validation report to include.
            name: The section's heading / sheet name.

        Returns:
            This builder, for chaining.
        """
        passed = sum(result.passed for result in report.results)
        narrative = f"{passed} of {len(report.results)} rule(s) passed."
        return self.add_dataframe(report.to_frame(), name, narrative)

    def add_comparison(self, result: ComparisonResult, name: str = "Comparison") -> "ReportBuilder":
        """Adds a `ComparisonResult` as a section: match rates plus the value-differences table.

        Args:
            result: The comparison result to include.
            name: The section's heading / sheet name.

        Returns:
            This builder, for chaining.
        """
        narrative = f"Key match rate: {result.key_match_rate:.1%}. Row match rate: {result.row_match_rate:.1%}."
        return self.add_dataframe(result.value_differences, name, narrative)

    def add_summary(self, summary: pd.DataFrame, name: str = "Summary") -> "ReportBuilder":
        """Adds a `AnalystStack.compare.summarize` output as a section.

        Args:
            summary: The summary DataFrame to include.
            name: The section's heading / sheet name.

        Returns:
            This builder, for chaining.
        """
        return self.add_dataframe(summary, name)

    def add_table_catalog(self, tables: pd.DataFrame, name: str = "Tables") -> "ReportBuilder":
        """Adds a connector's ``list_tables`` output as a section.

        Args:
            tables: The table-catalog DataFrame to include (see
                `AnalystStack.connectors.base.BaseConnector.list_tables`).
            name: The section's heading / sheet name.

        Returns:
            This builder, for chaining.
        """
        return self.add_dataframe(tables, name)

    def add_column_profile(self, profile: pd.DataFrame, name: str) -> "ReportBuilder":
        """Adds a connector's ``profile_columns`` output as a section.

        Args:
            profile: The column-profile DataFrame to include (see
                `AnalystStack.connectors.base.BaseConnector`'s ``profile_columns``).
            name: What to call the profiled table, e.g. ``"orders"`` -- shown as
                ``"Column Profile: <name>"``.

        Returns:
            This builder, for chaining.
        """
        return self.add_dataframe(profile, f"Column Profile: {name}")

    def build(self) -> DataQualityReport:
        """Finalizes the report.

        Returns:
            A `DataQualityReport` with every section added so far, in the order added.
        """
        return DataQualityReport(
            title=self.title,
            generated_at=pd.Timestamp.now(tz="UTC"),
            sections=list(self._sections),
        )
