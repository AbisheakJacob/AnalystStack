"""Result types produced by evaluating validation :class:`~AnalystStack.validate.rules.Rule` objects."""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CheckResult:
    """The outcome of evaluating a single ``Rule`` against a DataFrame.

    Returned by ``Rule.evaluate(df)`` and collected into a
    :class:`ValidationReport` by :meth:`AnalystStack.validate.validator.Validator.validate`.

    Attributes:
        rule: The rule's name, e.g. ``"not_null(price)"``.
        column: The column the rule targets, or ``None`` for whole-frame rules
            (e.g. those built with :func:`~AnalystStack.validate.rules.custom`).
        passed: ``True`` if every row satisfied the rule.
        failed_count: Number of rows that failed the rule.
        failed_indices: The DataFrame index labels of the failing rows.
    """

    rule: str
    column: str | None
    passed: bool
    failed_count: int
    failed_indices: list


@dataclass
class ValidationReport:
    """The combined outcome of every ``Rule`` a ``Validator`` evaluated.

    Returned by :meth:`AnalystStack.validate.validator.Validator.validate` — it never raises,
    so it's the right shape to log, write to a data-quality dashboard, or inspect
    interactively. Use :meth:`AnalystStack.validate.validator.Validator.enforce` instead when a
    failed check should stop execution.

    Attributes:
        results: One :class:`CheckResult` per rule that was evaluated, in the order
            the rules were added to the ``Validator``.
    """

    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """``True`` only if every rule in :attr:`results` passed."""
        return all(result.passed for result in self.results)

    def failures(self) -> list[CheckResult]:
        """Returns the subset of :attr:`results` that failed.

        Returns:
            The failing ``CheckResult`` objects, in evaluation order.
        """
        return [result for result in self.results if not result.passed]

    def to_frame(self) -> pd.DataFrame:
        """Renders the report as a DataFrame — one row per rule evaluated.

        Returns:
            A DataFrame with columns ``rule``, ``column``, ``passed``, and
            ``failed_count`` — one row per entry in :attr:`results`.
        """
        return pd.DataFrame(
            [
                {"rule": r.rule, "column": r.column, "passed": r.passed, "failed_count": r.failed_count}
                for r in self.results
            ]
        )
