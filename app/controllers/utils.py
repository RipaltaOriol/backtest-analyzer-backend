import json
import uuid
from io import StringIO

import pandas as pd


def parse_column_name(column_name):
    if (
        column_name.startswith(".m_")
        or column_name.startswith(".r_")
        or column_name.startswith(".d_")
    ):
        column_name = column_name[3:]
    elif column_name == ".tp":
        column_name = "Take Profit"
    elif column_name == ".sl":
        column_name = "Stop Loss"
    elif column_name == ".o":
        column_name = "Open"
    elif column_name == ".c":
        column_name = "Close"
    elif column_name == ".p":
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
    parsed_state = json.dumps(state["data"])
    # I personally do not like havving StringIO because I don't understand why is it necessary
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
