import json
import uuid
from datetime import date, datetime
from io import StringIO

import pandas as pd


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

    return column_name


def parse_column_type(column_type):
    if column_type == "object":
        return "string"
    elif column_type == "float64" or column_type == "int64":
        return "number"
    else:
        return str(column_type)


def from_db_to_df(state):
    """
    This methods converts a table from the database into a dataframe.
    """
    parsed_state = json.dumps(state["data"], default=json_serial)
    # I personally do not like having StringIO because I don't understand why is it necessary
    # although it doesn't work without it. Root problem from imgs being [] in json.
    return pd.read_json(StringIO(parsed_state), orient="index")


def from_df_to_db(df, add_index=False):
    """
    This methods converts a dataframe into a table to store in the database.
    """
    if add_index:
        new_index = pd.Series([uuid.uuid4().hex for _ in range(len(df))])
        df.set_index(new_index, inplace=True)

    data = df.to_json(orient="index", date_format="iso", date_unit="s")
    data = json.loads(data)

    return {"fields": df.dtypes.apply(lambda x: x.name).to_dict(), "data": data}
