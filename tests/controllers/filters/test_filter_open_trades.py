import pandas as pd
import pytest
from app.controllers.FilterController import filter_open_trades


def generate_data():
    """Creates a sample DataFrame for testing."""
    data = {
        "name": ["Alice", "Bob", "", "Charlie", None],
        "age": [25, 30, 35, None, 40],
        "appointment": ["2023-04-01", "2023-04-02", "", "2023-04-04", None],
    }
    df = pd.DataFrame(data)
    df["appointment"] = pd.to_datetime(df["appointment"], errors="coerce")
    return df


def test_filter_open_trades_empty():
    df = generate_data()
    result = filter_open_trades(
        df, column="name", column_type="object", operation="empty", value=None
    )
    assert len(result) == 2  # Expect rows with empty and None


def test_filter_open_trades_not_empty():
    df = generate_data()
    result = filter_open_trades(
        df, column="age", column_type="int64", operation="not_empty", value=None
    )
    assert len(result) == 4  # Excludes row with None


def test_filter_open_trades_equal():
    df = generate_data()
    result = filter_open_trades(
        df, column="age", column_type="int64", operation="equal", value=30
    )
    assert len(result) == 1 and result.iloc[0]["age"] == 30


def test_filter_open_trades_not_equal():
    df = generate_data()
    result = filter_open_trades(
        df, column="name", column_type="object", operation="not_equal", value="Bob"
    )
    assert len(result) == 4  # Excludes Bob


def test_filter_open_trades_higher_numeric():
    df = generate_data()
    result = filter_open_trades(
        df, column="age", column_type="int64", operation="higher", value=30
    )
    assert len(result) == 2  # Ages higher than 30


def test_filter_open_trades_lower_numeric():
    df = generate_data()
    result = filter_open_trades(
        df,
        column="age",
        column_type="int64",
        operation="lower",
        value=35,
    )
    assert len(result) == 2  # Ages lower than 35


def test_filter_open_trades_before_datetime():
    df = generate_data()
    result = filter_open_trades(
        df,
        column="appointment",
        column_type="datetime64",
        operation="before",
        value="04/02/2023",
    )
    assert len(result) == 1


def test_filter_open_trades_after_datetime():
    df = generate_data()
    result = filter_open_trades(
        df,
        column="appointment",
        column_type="datetime64",
        operation="after",
        value="04/01/2023",
    )
    assert len(result) == 2  # Dates after 04/01/2023


def test_filter_open_trades_error():
    df = generate_data()

    with pytest.raises(ValueError) as e:
        filter_open_trades(
            df,
            column="name",
            column_type="object",
            operation="invalid",
            value="redundant",
        )
    assert str(e.value) == "Something went wrong."
