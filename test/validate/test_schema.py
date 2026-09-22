"""Tests for AnalystStack.validate.schema."""

import pandas as pd
import pytest

from AnalystStack.exceptions.errors import ValidationError
from AnalystStack.validate.schema import check_schema, enforce_schema, schema_rule


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({"id": [1, 2, 3], "price": [10.0, 20.0, 30.0], "name": ["a", "b", "c"]})


def test_check_schema_passes_for_matching_list(df):
    result = check_schema(df, ["id", "price", "name"])
    assert result.passed
    assert result.missing_columns == []
    assert result.extra_columns == []


def test_check_schema_flags_missing_columns(df):
    result = check_schema(df, ["id", "price", "email"])
    assert not result.passed
    assert result.missing_columns == ["email"]


def test_check_schema_flags_extra_columns_only_when_strict(df):
    lenient = check_schema(df, ["id"], strict=False)
    assert lenient.passed
    assert lenient.extra_columns == []

    strict = check_schema(df, ["id"], strict=True)
    assert not strict.passed
    assert set(strict.extra_columns) == {"price", "name"}


def test_check_schema_flags_dtype_mismatches(df):
    result = check_schema(df, {"id": "int64", "price": "int64"})
    assert not result.passed
    assert result.dtype_mismatches == {"price": ("int64", "float64")}


def test_check_schema_dtype_spec_for_missing_column_is_not_a_dtype_mismatch(df):
    # "email" is missing entirely -- that's reported via missing_columns, not
    # dtype_mismatches (there's no dtype to compare against on a column that isn't there).
    result = check_schema(df, {"id": "int64", "email": "object"})
    assert result.missing_columns == ["email"]
    assert result.dtype_mismatches == {}


def test_check_schema_flags_order_mismatch(df):
    result = check_schema(df, ["price", "id", "name"], ordered=True)
    assert not result.passed
    assert result.order_mismatch is True


def test_check_schema_order_ignores_columns_not_in_expected(df):
    # "name" isn't in expected_columns, so its position shouldn't affect order_mismatch.
    result = check_schema(df, ["id", "price"], ordered=True)
    assert not result.order_mismatch


def test_enforce_schema_returns_df_on_success(df):
    result = enforce_schema(df, ["id", "price", "name"])
    pd.testing.assert_frame_equal(result, df)


def test_enforce_schema_raises_with_details(df):
    with pytest.raises(ValidationError, match="missing columns"):
        enforce_schema(df, ["id", "email"])


def test_enforce_schema_raises_with_every_kind_of_mismatch(df):
    # Triggers all four detail branches in one call: missing (email), extra (name, via
    # strict), dtype mismatch (price), and order mismatch (price before id).
    with pytest.raises(ValidationError) as exc_info:
        enforce_schema(df, {"price": "int64", "id": "int64", "email": "object"}, ordered=True, strict=True)

    message = str(exc_info.value)
    assert "missing columns" in message
    assert "unexpected columns" in message
    assert "dtype mismatches" in message
    assert "not in the expected order" in message


def test_schema_rule_integrates_with_rule_evaluate(df):
    rule = schema_rule(["id", "price", "name"])
    result = rule.evaluate(df)
    assert result.passed
    assert result.rule == "schema"


def test_schema_rule_fails_every_row_on_mismatch(df):
    rule = schema_rule(["id", "email"])
    result = rule.evaluate(df)
    assert not result.passed
    assert result.failed_count == len(df)
