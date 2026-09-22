"""Ensures safety before executing costly cloud operations"""

import re

from AnalystStack.exceptions.errors import ValidationError

_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def validate_identifier(identifier: str, label: str = "identifier") -> None:
    """Validates that a single identifier conforms to standard SQL naming rules.

    Args:
        identifier: A schema/dataset or table name to check.
        label: What to call `identifier` in the error message (e.g. ``"dataset ID"``),
            so callers get a message specific to what they passed.

    Raises:
        AnalystStack.exceptions.errors.ValidationError: If `identifier` contains anything
            other than letters, digits, and underscores.
    """
    if not _IDENTIFIER_PATTERN.match(identifier):
        raise ValidationError(f"Invalid {label}: {identifier}")


def validate_table_reference(dataset_id: str, table_id: str) -> None:
    """Validates that dataset and table IDs conform to standard SQL naming rules."""
    validate_identifier(dataset_id, "dataset ID")
    validate_identifier(table_id, "table ID")
