from datetime import datetime, timedelta

import pandas as pd


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
