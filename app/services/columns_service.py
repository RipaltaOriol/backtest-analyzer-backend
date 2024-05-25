import re

import numpy as np
import pandas as pd
from app.constants.columns import REQUIRED_COLUMNS


class ColumnsService:
    def __init__(self, df):
        self.df = df

    def add_required_columns(self):
        # Faster set-based column addition
        missing_columns = set(REQUIRED_COLUMNS) - set(self.df.columns)
        for column in missing_columns:
            self.df[column] = ""

    def validate_columns_dtypes(self):
        # TODO this can be optimized
        """
        Validates columns according to the specified column types.
        """
        for column in self.df.columns:
            # trade number
            if column == "#":
                self.df[column].astype(int)
            # pair
            elif column == "col_p":
                self.df[column].astype(str)
            # open price
            elif column == "col_o":
                self.df[column] = pd.to_numeric(df[column], errors="coerce")
            # close price
            elif column == "col_c":
                self.df[column] = pd.to_numeric(self.df[column], errors="coerce")
            # risk reward ratio
            elif column == "col_rr":
                self.df[column] = pd.to_numeric(self.df[column], errors="coerce")
            # stop loss
            elif column == "col_sl":
                self.df[column] = pd.to_numeric(self.df[column], errors="coerce")
            # take profit
            elif column == "col_tp":
                self.df[column] = pd.to_numeric(self.df[column], errors="coerce")
            # timeframe
            elif column == "col_t":
                self.df[column].astype(str)
            # direction
            elif column == "col_d":
                self.df[column] = np.where(
                    self.df[column].str.lower().isin(["long", "short"]),
                    self.df[column],
                    "",
                )
                self.df[column].astype(str)
            # dates
            elif column.startswith("col_d_"):
                self.df[column] = pd.to_datetime(
                    self.df[column], format="%d/%m/%y %H:%M:%S", utc=True
                )
            # results
            elif re.match(r"col_[vpr]_", column):
                self.df[column] = pd.to_numeric(self.df[column], errors="coerce")
