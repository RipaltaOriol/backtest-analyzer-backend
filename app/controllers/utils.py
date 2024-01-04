import json
import re
import uuid
from datetime import date, datetime
from io import StringIO

import numpy as np
import pandas as pd

TEMPLATE_PPT_POSITIONS = ["size", "order_type", "risk_reward", "price", "risk"]
TEMPLATE_PPT_TAKE_PROFIT = "take_profit"


class CustomJSONizer(json.JSONEncoder):
    def default(self, obj):
        return (
            super().encode(bool(obj))
            if isinstance(obj, np.bool_)
            else super().default(obj)
        )


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def parse_column_name(column_name):
    if (
        column_name.startswith("col_m_")
        or column_name.startswith("col_r_")
        or column_name.startswith("col_d_")
        or column_name.startswith("col_p_")
        or column_name.startswith("col_v_")
    ):
        column_name = column_name[6:]
    elif column_name == "col_tp":
        column_name = "Take Profit"
    elif column_name == "col_sl":
        column_name = "Stop Loss"
    elif column_name == "col_o":
        column_name = "Open"
    elif column_name == "col_c":
        column_name = "Close"
    elif column_name == "col_p":
        column_name = "Pair"
    elif column_name == "col_rr":
        column_name = "Risk Reward"
    elif column_name == "col_t":
        column_name = "Timeframe"
    elif column_name == "col_d":
        column_name = "Direction"
    return column_name


def get_result_decorator(column_name):
    if column_name.startswith("col_r_"):
        return " RR"
    elif column_name.startswith("col_p_"):
        return "%"
    else:
        return ""


def normalize_results(val, result):
    """
    Normalizes with % results
    """
    if result.startswith("col_p_"):
        return val * 100
    return val


def parse_column_type(column_type):
    if column_type == "object":
        return "string"
    elif column_type == "float64" or column_type == "int64":
        return "number"
    else:
        return str(column_type)


def from_db_to_df(state, orient="index"):
    """
    This methods converts a table from the database into a dataframe. It takes an
    orientation as an optional parameter which defaults to "index".
    """
    parsed_state = json.dumps(state["data"], default=json_serial)
    # get columns that have to be parsed to datetime
    date_columns = [
        column_name
        for column_name, dtype in state.get("fields").items()
        if dtype.startswith("datetime64")
    ]
    # I personally do not like having StringIO because I don't understand why is it necessary
    # although it doesn't work without it. Root problem from imgs being [] in json.
    return pd.read_json(
        StringIO(parsed_state), orient=orient, convert_dates=date_columns
    )


def from_df_to_db(df, add_index=False):
    """
    This methods converts a dataframe into a table to store in the database.
    """
    if add_index:
        new_index = pd.Series([uuid.uuid4().hex for _ in range(len(df))])
        df.set_index(new_index, inplace=True)

    data = df.to_json(orient="index", date_format="iso", date_unit="s")
    data = json.loads(data)

    # return {"fields": df.dtypes.apply(lambda x: x.name).to_dict(), "data": data}
    return data


def truncate(float, decimals):
    """Truncates/pads a float to decimal places without rounding"""
    s = "{}".format(float)
    if "e" in s or "E" in s:
        return "{0:.{1}f}".format(float, decimals)
    i, p, d = s.partition(".")
    return ".".join([i, (d + "0" * decimals)[:decimals]])


def parse_mappings(trade, template_k):
    # case for positions
    if template_k in TEMPLATE_PPT_POSITIONS:
        return trade["positions"][0][template_k]

    # case for take profit
    elif template_k == TEMPLATE_PPT_TAKE_PROFIT:
        return trade["take_profit"][0][template_k]

    else:
        return trade[template_k]


def row_to_ppt_template(mappings, template, row):

    for template_k, state_k in mappings.items():

        if state_k:

            value = row[state_k]

            if template_k in TEMPLATE_PPT_POSITIONS:
                template["positions"][0][
                    template_k
                ] = value  # I need to create a new object when its new

            # case for take profit
            elif template_k == TEMPLATE_PPT_TAKE_PROFIT:
                template["take_profit"][0][template_k] = value

            else:
                template[template_k] = value

    return template


def retrieve_filter_options(data: pd.DataFrame):
    """
    Accepts a DataFrame object from a Setup or Document and returns an array with the options to filter
    """
    options = []

    map_types = data.dtypes
    options = []
    for column in data.columns:
        if column.startswith("col_m_"):
            option = {"id": column, "name": column[6:]}
            if map_types[column] == "float64" or map_types[column] == "int64":
                option.update(type="number")
            else:
                option.update(type="string")
                option.update(values=list(data[column].dropna().unique()))
            options.append(option)
        if column == "col_p":
            option = {
                "id": column,
                "name": "Pair",
                "type": "string",
                "values": list(data[column].dropna().unique().astype(str)),
            }
            options.append(option)
        if column == "col_rr":
            option = {
                "id": column,
                "name": "Risk Reward",
                "type": "number",
                "values": list(data[column].dropna().unique()),
            }
            options.append(option)
        if column.startswith("col_d_"):
            option = {
                "id": column,
                "name": column[6:],
                "type": "date",
            }
            options.append(option)
    options = json.loads(json.dumps(options, cls=CustomJSONizer))
    return options


def validation_pipeline(data):
    """
    This helper function validates and sanitizes the data before returning it
    to be added to the database.
    """
    # TODO create test for this function
    for column in data.keys():
        # sanitizes and parses percentage columns
        if re.match(r"col_p_", column):
            # check if value is present
            if data[column]:
                data[column] = float(data[column]) / 100
            else:
                data[column] = None

    return data
