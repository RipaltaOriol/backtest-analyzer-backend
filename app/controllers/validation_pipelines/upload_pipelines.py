import re

import numpy as np
import pandas as pd


def df_column_datatype_validation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates that the columns included in the document/DataFrame are valid according
    to the specified column types.

    It takes in a a DataFrame and returns the same DataFrame with the values parsed to the
    corresponding column types.
    """
    for column in df.columns:
        # trade number
        if column == "#":
            df[column].astype(int)
        # pair
        elif column == "col_p":
            df[column].astype(str)
        # open price
        elif column == "col_o":
            df[column] = pd.to_numeric(df[column], errors="coerce")
        # close price
        elif column == "col_c":
            df[column] = pd.to_numeric(df[column], errors="coerce")
        # risk reward ratio
        elif column == "col_rr":
            df[column] = pd.to_numeric(df[column], errors="coerce")
        # stop loss
        elif column == "col_sl":
            df[column] = pd.to_numeric(df[column], errors="coerce")
        # take profit
        elif column == "col_tp":
            df[column] = pd.to_numeric(df[column], errors="coerce")
        # timeframe
        elif column == "col_t":
            df[column].astype(str)
        # direction
        elif column == "col_d":
            df[column] = np.where(
                df[column].str.lower().isin(["long", "short"]), df[column], ""
            )
            df[column].astype(str)
        # dates
        elif column.startswith("col_d_"):
            df[column] = pd.to_datetime(
                df[column], format="%d/%m/%y %H:%M:%S", utc=True
            )
        # results
        elif re.match(r"col_[vpr]_", column):
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df
