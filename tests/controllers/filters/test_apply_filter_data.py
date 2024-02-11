import pandas as pd
from pandas.tseries.offsets import DateOffset

unfiltered_data = pd.DataFrame(
    {
        "asset": ["A", "B", "C", "C", "B", "B", "B", "D", "A", "C"],
        "numeric_metric": [0.78, 0.78, 0.5, 0.23, 0.5, 0.5, 1.21, 1.6, 1.21, 0.5],
        "date": pd.date_range(start="2018-04-27", periods=10, freq=DateOffset(days=7)),
    }
)


filtered_data_date = pd.DataFrame(
    {
        "asset": ["B", "C", "C", "B"],
        "numeric_metric": [0.78, 0.5, 0.23, 0.5],
        "date": pd.to_datetime(
            ["2018-05-04", "2018-05-11", "2018-05-18", "2018-05-25"]
        ),
    },
    index=[1, 2, 3, 4],
)
