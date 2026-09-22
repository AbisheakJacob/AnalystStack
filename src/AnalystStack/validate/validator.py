"""The ``Validator`` class: bundles ``Rule`` objects and applies them in one call."""

import pandas as pd

from AnalystStack.exceptions.errors import ValidationError
from AnalystStack.validate.results import ValidationReport
from AnalystStack.validate.rules import Rule


class Validator:
    """Bundles ``Rule`` objects together and applies them to a DataFrame in one call.

    Build a list of rules with the factory functions in
    :mod:`AnalystStack.validate.rules` (``not_null``, ``unique``, ``in_range``, ``is_in``,
    ``matches_regex``, ``has_dtype``, ``custom``), pass them to a ``Validator``, then call
    :meth:`validate` for a report or :meth:`enforce` to raise on failure.

    Choosing between the two:

    * Use **``validate(df)``** when you want a report to inspect, log, or write to a
      data-quality dashboard — it always returns a ``ValidationReport`` and never raises.
    * Use **``enforce(df)``** as a guard at a pipeline boundary — e.g. right before
      writing to a warehouse — where a failed check should stop execution. It raises
      ``AnalystStack.exceptions.errors.ValidationError`` with every failing rule listed in
      the message, and otherwise returns ``df`` unchanged so it can be chained inline.

    Example:
        ```python
        from AnalystStack.validate import Validator, not_null, unique, in_range

        validator = Validator([
            not_null("price"),
            unique("id"),
            in_range("price", min_value=0),
        ])

        report = validator.validate(df)   # never raises
        report.passed                     # False
        report.failures()                 # [CheckResult(rule="in_range(price)", ...)]
        report.to_frame()                 # one row per rule, as a DataFrame

        validator.enforce(df)             # raises ValidationError describing every failed rule
        ```
    """

    def __init__(self, rules: list[Rule] | None = None):
        """Initializes the validator.

        Args:
            rules: The rules to bundle. Defaults to an empty list — use :meth:`add` to
                build the set up incrementally.
        """
        self.rules: list[Rule] = list(rules or [])

    def add(self, rule: Rule) -> "Validator":
        """Adds a rule and returns self, so calls can be chained.

        Args:
            rule: The rule to append.

        Returns:
            This ``Validator``, so calls can be chained, e.g.
            ``Validator().add(not_null("id")).add(unique("id"))``.
        """
        self.rules.append(rule)
        return self

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """Evaluates every rule and returns a report — never raises.

        Args:
            df: The DataFrame to check.

        Returns:
            A :class:`~AnalystStack.validate.results.ValidationReport` with one
            ``CheckResult`` per rule, in the order the rules were added.
        """
        return ValidationReport(results=[rule.evaluate(df) for rule in self.rules])

    def enforce(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validates ``df`` and raises if any rule fails; returns ``df`` unchanged otherwise.

        Args:
            df: The DataFrame to check.

        Returns:
            ``df``, unchanged, if every rule passed.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If one or more rules failed.
                The message lists every failing rule and how many rows it affected.
        """
        report = self.validate(df)
        failures = report.failures()
        if failures:
            details = "; ".join(f"{f.rule} failed on {f.failed_count} row(s)" for f in failures)
            raise ValidationError(f"DataFrame failed validation: {details}")
        return df
