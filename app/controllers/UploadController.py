import json

import numpy as np
import pandas as pd
from app.controllers.utils import from_df_to_db
from flask import jsonify

REQUIRED_COLUMNS = ["note", "imgs"]


def upload_default(file):
    # check that it is a CSV file
    if file.content_type == "text/csv":

        # transform Dataframe
        df = pd.read_csv(file, keep_default_na=False)

        # if date column included it parses it
        if ".d" in df.columns:
            df[".d"] = pd.to_datetime(df[".d"])
        # include in how-to
        # drop emtpy rows / columns
        # df.dropna(axis = 1, inplace=True)

        # add all required columns
        df = _add_required_columns(df)

        # parse images from CSV
        df["imgs"] = df["imgs"].apply(lambda x: x.split("^") if x else [])

        return from_df_to_db(df, add_index=True)
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

    # parse dates
    df.loc[:, "Open Time"] = pd.to_datetime(df["Open Time"], format="%Y.%m.%d %H:%M:%S")
    df.loc[:, "Close Time"] = pd.to_datetime(
        df["Open Time"], format="%Y.%m.%d %H:%M:%S"
    )

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
        df.loc[:, col] = df[col].apply(lambda x: str(x).replace(" ", ""))

    df = df.astype(convert_dict)

    for col in ["Open Time", "Close Time"]:
        df.loc[:, col] = pd.to_datetime(df[col])

    rename_columns = {
        "Ticket": "#",
        "Open Time": "col_d_Open Time",
        "Type": "col_m_Type",
        "Size": "col_m_Size",
        "Item": "col_p",
        "Open": "col_o",
        "S / L": "col_sl",
        "T / P": "col_tp",
        "Close Time": "col_d_Close Time",
        "Close": "col_c",
        "Commission": "col_m_Commision",
        "Taxes": "col_m_Taxes",
        "Swap": "col_m_Swap",
        "Profit": "col_r_Profit",
    }

    df.rename(columns=rename_columns, errors="raise", inplace=True)

    # add all required columns
    df = _add_required_columns(df)
    return from_df_to_db(df, add_index=True)


def _add_required_columns(df):
    for col in REQUIRED_COLUMNS:
        if not col in df.columns:
            df[col] = ""

    return df
