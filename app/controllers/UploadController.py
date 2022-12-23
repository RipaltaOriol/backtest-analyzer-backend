import json

import numpy as np
import pandas as pd
from flask import jsonify


def upload_default(file):
    # check that it is a CSV file
    if file.content_type == "text/csv":

        # transform Dataframe
        df = pd.read_csv(file)

        # if date column included it parses it
        if ".d" in df.columns:
            df[".d"] = pd.to_datetime(df[".d"])
        # include in how-to
        # drop emtpy rows / columns
        # df.dropna(axis = 1, inplace=True)
        df = df.to_json(orient="table")
        df = json.loads(df)
        return df
    else:
        # NOTE: change this to pass the error, otherwise it will fail
        return jsonify({"msg": "File is not an accepted format", "success": False})


def upload_mt4(file):
    data = pd.read_excel(file, index_col=False)

    start = data.index[data["Raw Trading Ltd"] == "Ticket"].tolist()[0]
    end = data.index[data["Raw Trading Ltd"] == "Open Trades:"].tolist()[0]

    df = data[start : end - 2]
    df.columns = df.iloc[0]
    df.columns.name = None

    df.drop(index=df.index[0:2], axis=0, inplace=True)
    df.index = np.arange(1, len(df) + 1)

    # rename prices columns to open & close
    new_cols = []
    price_cols_name = ["Close", "Open"]
    for col in df.columns.tolist():
        if col == "Price":
            new_cols.append(price_cols_name.pop())
        else:
            new_cols.append(col)
    df.columns = new_cols

    convert_dict = {
        "Size": "float",
        "Open": "float",
        "S / L": "float",
        "T / P": "float",
        "Commission": "float",
        "Taxes": "float",
        "Close": "float",
        "Swap": "float",
        "Profit": "float",
    }

    # change column types
    for col in convert_dict:
        df[col] = df[col].apply(lambda x: str(x).replace(" ", ""))

    df = df.astype(convert_dict)

    for col in ["Open Time", "Close Time"]:
        df[col] = pd.to_datetime(df[col])

    rename_columns = {
        "Ticket": "#",
        "Open Time": ".d_Open Time",
        "Type": ".m_Type",
        "Size": ".m_Size",
        "Item": ".p",
        "Open": ".o",
        "S / L": ".sl",
        "T / P": ".tp",
        "Close Time": ".d_Close Time",
        "Close": ".c",
        "Commission": ".m_Commision",
        "Taxes": ".m_Taxes",
        "Swap": ".m_Swap",
        "Profit": ".r_Profit",
    }

    df.rename(columns=rename_columns, errors="raise", inplace=True)

    df = df.to_json(orient="table")
    df = json.loads(df)
    return df
