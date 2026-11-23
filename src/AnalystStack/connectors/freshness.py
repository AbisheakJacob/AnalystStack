"""Freshness check: how old is the newest value in a timestamp column?

The default column, ``syncstartdatetime``, is the load timestamp used by the analyst's
warehouse tables; pass another column name for other tables.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd

from AnalystStack.exceptions.errors import QueryExecutionError, ValidationError
from AnalystStack.utils.validation import validate_identifier

DEFAULT_COLUMN = "syncstartdatetime"
_TABLE_PATH = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+){0,2}$")


@dataclass(frozen=True)
class FreshnessResult:
    """The outcome of a freshness check.

    Attributes:
        table: The table that was checked.
        column: The timestamp column.
        max_value: The newest timestamp, or ``None`` if the table or column is empty.
        age_hours: Hours between ``max_value`` and now (timestamps without a time zone are
            treated as UTC), or ``None`` when there is no value.
        sql: The statement that was run.
    """

    table: str
    column: str
    max_value: pd.Timestamp | None
    age_hours: float | None
    sql: str

    def is_fresh(self, max_age_hours: float) -> bool:
        """True if there is a value and it is no older than ``max_age_hours``."""
        return self.age_hours is not None and self.age_hours <= max_age_hours


def freshness_sql(table: str, column: str = DEFAULT_COLUMN) -> str:
    """Builds ``SELECT MAX(column) AS max_value FROM table`` after validating both names.

    Raises:
        AnalystStack.exceptions.errors.ValidationError: If either name is not a plain
            identifier path (letters, digits, underscores, up to three dot-separated parts).
    """
    if not _TABLE_PATH.match(table):
        raise ValidationError(f"Invalid table reference: {table}")
    validate_identifier(column, "column name")
    return f"SELECT MAX({column}) AS max_value FROM {table}"


def check_freshness(
    connector, table: str, column: str = DEFAULT_COLUMN, now: datetime | None = None
) -> FreshnessResult:
    """Runs the freshness query and measures the age of the newest value.

    Args:
        connector: Any connector with ``read_data``.
        table: ``schema.table`` (or ``project.dataset.table``).
        column: The timestamp column; defaults to ``syncstartdatetime``.
        now: The reference time (UTC); defaults to the current time.

    Returns:
        The result, with ``age_hours`` ``None`` if the column holds no values.

    Raises:
        AnalystStack.exceptions.errors.ValidationError: If the names are invalid.
        AnalystStack.exceptions.errors.QueryExecutionError: If the query fails or returns an
            unexpected shape.
    """
    sql = freshness_sql(table, column)
    frame = connector.read_data(sql)
    if frame.shape != (1, 1):
        raise QueryExecutionError("Freshness query returned an unexpected shape.")
    raw = frame.iloc[0, 0]
    if pd.isna(raw):
        return FreshnessResult(table, column, None, None, sql)
    stamp = pd.Timestamp(raw)
    stamp = stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
    reference = pd.Timestamp(now or datetime.now(UTC))
    reference = reference.tz_localize("UTC") if reference.tzinfo is None else reference.tz_convert("UTC")
    return FreshnessResult(table, column, stamp, (reference - stamp).total_seconds() / 3600, sql)
