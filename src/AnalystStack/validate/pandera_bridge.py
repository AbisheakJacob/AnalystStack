"""Optional bridge from pandera's failure output into this package's `ValidationReport` shape.

`pandera <https://pandera.readthedocs.io/>`_ is not a dependency of AnalystStack -- install
it yourself (``pip install "AnalystStack[pandera]"``) if you want its schema-coercion or
hypothesis-style checks. This module converts what pandera raises into a
`AnalystStack.validate.results.ValidationReport`, so anything already built to consume one
(e.g. `AnalystStack.report`) works the same whether a check came from this package's own
`AnalystStack.validate.rules.Rule`\\ s or from a pandera schema. `pandera` is imported only
inside this module's own function, never from `AnalystStack.validate`'s top-level surface,
so plain ``import AnalystStack`` never requires it.

`AnalystStack.validate.schema.check_schema`/``enforce_schema`` remain the default,
dependency-free option for schema validation -- reach for pandera (via this bridge) only
when you specifically need its coercion or hypothesis-style checks.
"""

from typing import TYPE_CHECKING

from AnalystStack.validate.results import CheckResult, ValidationReport

if TYPE_CHECKING:
    import pandera.errors


def pandera_errors_to_report(exc: "pandera.errors.SchemaErrors") -> ValidationReport:
    """Converts a pandera `SchemaErrors` exception into a `ValidationReport`.

    Args:
        exc: The `pandera.errors.SchemaErrors` raised by
            ``DataFrameSchema.validate(df, lazy=True)``.

    Returns:
        A `ValidationReport` with one `CheckResult` per distinct ``(column, check)`` pair
        pandera flagged, aggregating every failing row under that check -- so, unlike
        pandera's own row-per-failure `failure_cases` table, this groups the way
        `AnalystStack.validate.results.ValidationReport.to_frame` and
        `AnalystStack.report` expect.

    Example:
        ```python
        import pandera.pandas as pa
        from AnalystStack.validate.pandera_bridge import pandera_errors_to_report

        schema = pa.DataFrameSchema({"price": pa.Column(float, pa.Check.ge(0))})
        try:
            schema.validate(df, lazy=True)
        except pa.errors.SchemaErrors as exc:
            report = pandera_errors_to_report(exc)
        ```
    """
    failure_cases = exc.failure_cases
    group_cols = [c for c in ("column", "check") if c in failure_cases.columns]

    results = []
    for keys, group in failure_cases.groupby(group_cols, dropna=False):
        info = dict(zip(group_cols, keys, strict=True))
        column = info.get("column")
        check_name = info.get("check") or "check"
        failed_indices = group["index"].dropna().tolist() if "index" in group.columns else []
        results.append(
            CheckResult(
                rule=f"pandera:{check_name}",
                column=column if isinstance(column, str) else None,
                passed=False,
                failed_count=len(group),
                failed_indices=failed_indices,
            )
        )
    return ValidationReport(results=results)
