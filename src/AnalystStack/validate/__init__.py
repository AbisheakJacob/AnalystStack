"""Declarative validation for pandas DataFrames.

Makes it cheap to attach a handful of sanity checks to a DataFrame — particularly one
you just read from a warehouse or are about to write back to one — without reaching for a
heavyweight schema library.

Build a list of :class:`~AnalystStack.validate.rules.Rule` objects with the factory
functions in :mod:`AnalystStack.validate.rules` (:func:`not_null`, :func:`unique`,
:func:`in_range`, :func:`is_in`, :func:`matches_regex`, :func:`has_dtype`,
:func:`row_count_between`, :func:`no_duplicate_rows`, :func:`is_fresh`, :func:`no_outliers`,
:func:`custom`), bundle them into a :class:`~AnalystStack.validate.validator.Validator`, then
call ``.validate()`` for a report or ``.enforce()`` to raise on failure. See
:class:`~AnalystStack.validate.validator.Validator` for the full guidance on choosing
between the two.

Three more specialized checks live in their own submodules (not re-exported here, to keep
this package importable with no extra dependencies) and each offers a `Rule`-adapter so it
composes with a `Validator` alongside the checks above:

* :mod:`AnalystStack.validate.schema` — whole-frame structural checks (column
  existence/order/dtype): :func:`~AnalystStack.validate.schema.check_schema`,
  :func:`~AnalystStack.validate.schema.enforce_schema`,
  :func:`~AnalystStack.validate.schema.schema_rule`.
* :mod:`AnalystStack.validate.drift` — statistical drift between two snapshots of a column:
  :func:`~AnalystStack.validate.drift.population_stability_index`,
  :func:`~AnalystStack.validate.drift.ks_test` (requires ``AnalystStack[stats]``),
  :func:`~AnalystStack.validate.drift.compare_dataframe_drift`.
* :mod:`AnalystStack.validate.referential` — referential integrity between two DataFrames:
  :func:`~AnalystStack.validate.referential.check_referential_integrity`,
  :func:`~AnalystStack.validate.referential.referential_integrity_rule`.

A fourth, :mod:`AnalystStack.validate.pandera_bridge`, converts
`pandera <https://pandera.readthedocs.io/>`_ failures into a `ValidationReport` for teams
that want pandera's coercion/hypothesis-style checks (requires ``AnalystStack[pandera]``).

Defining a reusable, named set of rules: a `Validator` is just a list of `Rule` objects, so
"build once, use everywhere" is a plain Python function you write yourself, e.g.::

    def orders_suite() -> Validator:
        return Validator([not_null("price"), unique("id"), row_count_between(min_value=1)])

There's deliberately no YAML/JSON rule-suite format — :func:`custom` rules are arbitrary
Python closures, and serializing arbitrary code safely isn't possible without an
``eval``/``exec``-style hole.
"""

from AnalystStack.validate.results import CheckResult, ValidationReport
from AnalystStack.validate.rules import (
    Rule,
    custom,
    has_dtype,
    in_range,
    is_fresh,
    is_in,
    matches_regex,
    no_duplicate_rows,
    no_outliers,
    not_null,
    row_count_between,
    unique,
)
from AnalystStack.validate.validator import Validator

__all__ = [
    "CheckResult",
    "ValidationReport",
    "Rule",
    "Validator",
    "not_null",
    "unique",
    "in_range",
    "is_in",
    "matches_regex",
    "has_dtype",
    "row_count_between",
    "no_duplicate_rows",
    "is_fresh",
    "no_outliers",
    "custom",
]
