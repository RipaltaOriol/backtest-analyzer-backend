import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from app.controllers.utils import parse_column_name
from app.utils.custom_jsonizer import serialize_to_json


class FilterService:
    # Define operations as a static class variable
    OPERATIONS = {
        "in": "filter_in",
        "nin": "filter_nin",
        "date": "filter_date",
        "gt": "filter_gt",
        "lt": "filter_lt",
        "eq": "filter_eq",
        "ne": "filter_ne",
    }

    def get_filter_options(self, df: pd.DataFrame):
        """
        Returns an array of filter options for columns in a DataFrame that meet specific criteria.
        Includes error handling to manage issues with DataFrame processing or JSON serialization.
        """
        try:
            df.replace({np.nan: None}, inplace=True)
            options = {
                col: self.generate_filter_option(col, df[col])
                for col in df.columns
                if col.startswith("col_")
            }
            json_options = serialize_to_json(
                options
            )  # Use the abstracted JSON conversion function
            return json_options, None

        except Exception as e:
            # Handle general errors that could occur during option generation or serialization
            error_message = f"Failed to retrieve filter options due to: {str(e)}"
            logging.err(error_message)
            return None, error_message

    def generate_filter_option(self, column_name, column_data):
        """
        Generates a filter option dictionary for a specified DataFrame column based on its type and prefix.
        """
        option = {
            "id": column_name,
            "name": parse_column_name(column_name),
            "type": "number" if column_data.dtype in ["float64", "int64"] else "string",
        }
        if column_name.startswith("col_m_"):
            option["values"] = (
                list(column_data.dropna().unique())
                if option["type"] == "string"
                else None
            )
        elif column_name.startswith("col_d_"):
            option["type"] = "date"
        elif column_name == "col_p":
            option["values"] = list(column_data.dropna().unique().astype(str))
        elif column_name == "col_d":
            option["values"] = ["Long", "Short"]
        return option

    def apply_filter(self, df, filter_obj) -> None:
        """
        Routes to the specific filtering method based on the operation specified in filter_obj.
        Raises ValueError for unsupported operations.
        """
        method_name = self.OPERATIONS.get(filter_obj.operation)
        if not method_name:
            raise ValueError("Unsupported operation")

        # Handle boolean and date operations separately
        if (
            filter_obj.operation in ["in", "nin"]
            and df.dtypes[filter_obj.column] == "bool"
            and len(filter_obj.value) == 1
        ):
            return self.filter_boolean(df, filter_obj)
        elif hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(df, filter_obj)
        else:
            raise ValueError("Unsupported operation")

    def filter_boolean(self, df, filter_obj):
        """
        Filters dataframe for boolean operations 'in' and 'nin'.
        """
        value_bool = filter_obj.value[0] == "true"
        if filter_obj.operation == "in":
            return df[df[filter_obj.column] == value_bool]
        elif filter_obj.operation == "nin":
            return df[df[filter_obj.column] != value_bool]

    def filter_in(self, df, filter_obj):
        if filter_obj.column == "col_d":
            return df[
                df[filter_obj.column].str.fullmatch(
                    "|".join(filter_obj.value), case=False
                )
            ]
        else:
            return df[df[filter_obj.column].isin(filter_obj.value)]

    def filter_nin(self, df, filter_obj):
        if filter_obj.column == "col_d":
            return df[
                -df[filter_obj.column].str.fullmatch(
                    "|".join(filter_obj.value), case=False
                )
            ]
        else:
            return df[-df[filter_obj.column].isin(filter_obj.value)]

    def filter_date(self, df, filter_obj):
        """
        Filters dataframe for entries between two dates.
        """
        date_from = datetime.strptime(filter_obj.value[0], "%m/%d/%Y").strftime(
            "%Y-%m-%d"
        )
        date_to = datetime.strptime(filter_obj.value[1], "%m/%d/%Y") + timedelta(days=1)
        date_to = date_to.strftime("%Y-%m-%d")
        return df.loc[
            (df[filter_obj.column] >= date_from) & (df[filter_obj.column] < date_to)
        ]

    def filter_gt(self, df, filter_obj):
        return df[df[filter_obj.column] > filter_obj.value[0]]

    def filter_lt(self, df, filter_obj):
        return df[df[filter_obj.column] < filter_obj.value[0]]

    def filter_eq(self, df, filter_obj):
        return df[df[filter_obj.column] == filter_obj.value[0]]

    def filter_ne(self, df, filter_obj):
        return df[df[filter_obj.column] != filter_obj.value[0]]
