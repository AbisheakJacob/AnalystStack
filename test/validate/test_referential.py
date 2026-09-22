"""Tests for AnalystStack.validate.referential."""

import pandas as pd
import pytest

from AnalystStack.validate import Validator
from AnalystStack.validate.referential import check_referential_integrity, referential_integrity_rule


@pytest.fixture
def customers() -> pd.DataFrame:
    return pd.DataFrame({"id": [1, 2, 3]})


@pytest.fixture
def orders() -> pd.DataFrame:
    return pd.DataFrame({"order_id": [100, 101, 102, 103], "customer_id": [1, 2, 99, None]})


def test_check_referential_integrity_flags_dangling_references(orders, customers):
    result = check_referential_integrity(orders, "customer_id", customers, "id")
    assert not result.passed
    # index 2 (customer_id=99) fails; index 3 (None) passes since allow_null defaults True
    assert result.failed_indices == [2]


def test_check_referential_integrity_can_reject_nulls(orders, customers):
    result = check_referential_integrity(orders, "customer_id", customers, "id", allow_null=False)
    assert result.failed_indices == [2, 3]


def test_check_referential_integrity_passes_for_clean_data(customers):
    orders = pd.DataFrame({"customer_id": [1, 2, 3]})
    result = check_referential_integrity(orders, "customer_id", customers, "id")
    assert result.passed


def test_referential_integrity_rule_integrates_with_validator(orders, customers):
    rule = referential_integrity_rule(customers, "id", child_column="customer_id")
    validator = Validator([rule])
    report = validator.validate(orders)

    assert not report.passed
    failure = report.failures()[0]
    assert failure.failed_indices == [2]


def test_referential_integrity_rule_defaults_child_column_to_parent_column():
    parent = pd.DataFrame({"id": [1, 2]})
    child = pd.DataFrame({"id": [1, 2, 3]})
    rule = referential_integrity_rule(parent, "id")
    result = rule.evaluate(child)
    assert result.failed_indices == [2]
