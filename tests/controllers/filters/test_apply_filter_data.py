import pandas as pd
from pandas.tseries.offsets import DateOffset

unfiltered_data = pd.DataFrame(
    {
        "asset": ["A", "B", "C", "C", "B", "B", "B", "D", "A", "C"],
        "numeric_metric": [0.78, 0.78, 0.5, 0.23, 0.5, 0.5, 1.21, 1.6, 1.21, 0.5],
        "date": pd.date_range(start="2018-04-27", periods=10, freq=DateOffset(days=7)),
        "col_d": [
            "Long",
            "Short",
            "SHORT",
            "SHORT",
            "LONG",
            "LonG",
            "sHoRt",
            "SHoRt",
            "LoNG",
            "long",
        ],
    }
)


filtered_data_date = pd.DataFrame(
    {
        "asset": ["B", "C", "C", "B"],
        "numeric_metric": [0.78, 0.5, 0.23, 0.5],
        "date": pd.to_datetime(
            ["2018-05-04", "2018-05-11", "2018-05-18", "2018-05-25"]
        ),
        "col_d": ["Short", "SHORT", "SHORT", "LONG"],
    },
    index=[1, 2, 3, 4],
)

filtered_data_direction_include = pd.DataFrame(
    {
        "asset": ["A", "B", "B", "A", "C"],
        "numeric_metric": [0.78, 0.5, 0.5, 1.21, 0.5],
        "date": pd.to_datetime(
            ["2018-04-27", "2018-05-25", "2018-06-01", "2018-06-22", "2018-06-29"]
        ),
        "col_d": ["Long", "LONG", "LonG", "LoNG", "long"],
    },
    index=[0, 4, 5, 8, 9],
)


filtered_data_direction_exclude = pd.DataFrame(
    {
        "asset": ["B", "C", "C", "B", "D"],
        "numeric_metric": [0.78, 0.5, 0.23, 1.21, 1.6],
        "date": pd.to_datetime(
            ["2018-05-04", "2018-05-11", "2018-05-18", "2018-06-08", "2018-06-15"]
        ),
        "col_d": ["Short", "SHORT", "SHORT", "sHoRt", "SHoRt"],
    },
    index=[1, 2, 3, 6, 7],
)
