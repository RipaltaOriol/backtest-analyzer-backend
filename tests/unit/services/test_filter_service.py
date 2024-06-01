import logging

import pandas as pd
import pytest
from app.services.filter_service import FilterService


# Assuming serialize_to_json is a simple wrapper around json.dumps
def mock_serialize_to_json(data):
    return data  # return the data for simplicity in testing


@pytest.fixture
def filtering_service():
    service = FilterService()
    return service


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "col_m_profit": [100, 200, 300],
            "col_d_date": pd.to_datetime(["2021-01-01", "2021-01-02", "2021-01-03"]),
            "col_p": ["EURUSD", "USDJPY", "GBPUSD"],
            "col_d": ["Long", "Short", "Long"],
        }
    )


def test_get_filter_options_success(filtering_service, sample_data, mocker):
    mocker.patch("app.utils.custom_jsonizer.serialize_to_json", mock_serialize_to_json)
    result, error = filtering_service.get_filter_options(sample_data)
    assert error is None
    result_value = list(result.values())
    assert isinstance(result, object)  # check if the result is a list
    assert "id" in result_value[0]  # check if 'id' key is present in the result options


def test_generate_option_for_column_numeric(filtering_service, sample_data):
    result = filtering_service.generate_filter_option(
        "col_m_profit", sample_data["col_m_profit"]
    )
    assert result["type"] == "number"
    assert result["id"] == "col_m_profit"


def test_generate_option_for_column_date(filtering_service, sample_data):
    result = filtering_service.generate_filter_option(
        "col_d_date", sample_data["col_d_date"]
    )
    assert result["type"] == "date"
    assert result["name"] == "date"
