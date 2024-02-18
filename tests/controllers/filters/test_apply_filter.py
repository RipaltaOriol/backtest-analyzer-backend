from app.controllers.FilterController import apply_filter
from pandas.testing import assert_frame_equal
from tests.controllers.filters.test_apply_filter_data import (
    filtered_data_date,
    filtered_data_direction_exclude,
    filtered_data_direction_include,
    unfiltered_data,
)


def test_apply_filters_date():
    filtered_df = apply_filter(
        unfiltered_data, "date", "date", ["05/01/2018", "05/30/2018"]
    )
    assert_frame_equal(filtered_df, filtered_data_date)


def test_apply_filters_direction_include():
    filtered_df = apply_filter(unfiltered_data, "col_d", "in", ["long"])
    assert_frame_equal(filtered_df, filtered_data_direction_include)


def test_apply_filters_direction_exclude():
    filtered_df = apply_filter(unfiltered_data, "col_d", "nin", ["LONG"])
    assert_frame_equal(filtered_df, filtered_data_direction_exclude)


def test_apply_filters_direction_all():
    filtered_df = apply_filter(unfiltered_data, "col_d", "in", ["Long", "Short"])
    assert_frame_equal(filtered_df, unfiltered_data)
