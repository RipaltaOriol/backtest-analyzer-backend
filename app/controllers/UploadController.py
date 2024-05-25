import json
import re

import numpy as np
import pandas as pd
from app.constants.columns import (
    REQUIRED_COLUMNS,
    get_mt_columns_rename,
    get_mt_target_columns,
)
from app.controllers.errors import UploadError
from app.controllers.utils import from_df_to_db
from app.controllers.validation_pipelines.upload_pipelines import (
    df_column_datatype_validation,
)


def upload_default(file):
    # check that it is a CSV file
    if file.content_type == "text/csv":

        # transform Dataframe
        df = pd.read_csv(file, keep_default_na=False)

        # TODO: in docs make a note for how to add percentages

        try:
            df = df_column_datatype_validation(df)
        except ValueError as e:
            raise UploadError(
                "One or more column values are miscellaneous and do not satisfy typing conditions."
            )

        # add all required columns
        df = _add_required_columns(df)

        # give default values to imgs and note columns if blank
        df["imgs"] = df["imgs"].fillna("")
        df["note"] = df["note"].fillna("")
        # parse images from CSV
        df["imgs"] = df["imgs"].apply(lambda x: x.split("^") if x else [])
        state = {
            "data": from_df_to_db(df, add_index=True),
            "fields": df.dtypes.apply(lambda x: x.name).to_dict(),
        }

        return state
    else:
        raise UploadError("File is not an accepted format.")


def upload_mt4(file):
    data = pd.read_excel(file, index_col=False)

    start = data.index[data.iloc[:, 0] == "Ticket"].tolist()[0]
    end = data.index[data.iloc[:, 0] == "Open Trades:"].tolist()[0]

    df = data[start : end - 2]
    df.columns = df.iloc[0]
    df.columns.name = None

    df.drop(index=df.index[0:1], axis=0, inplace=True)
    df = df[df["Type"] != "balance"]  # remove balance deposit
    df = df[df["Commission"] != "cancelled"]  # remove cancelled trades

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
    df["Open Time"] = pd.to_datetime(
        df["Open Time"], format="%Y.%m.%d %H:%M:%S", utc=True
    )
    df["Close Time"] = pd.to_datetime(
        df["Close Time"], format="%Y.%m.%d %H:%M:%S", utc=True
    )
    # NOTE: the method in below does not work:
    # https://github.com/pandas-dev/pandas/issues/53729
    # df.loc[:, "Open Time"] = pd.to_datetime(
    #     df["Open Time"], format="%Y.%m.%d %H:%M:%S", utc=True
    # )
    # df.loc[:, "Close Time"] = pd.to_datetime(
    #     df["Close Time"], format="%Y.%m.%d %H:%M:%S", utc=True
    # )

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
        "Profit": "col_v_Profit",
    }

    df.rename(columns=rename_columns, errors="raise", inplace=True)

    # TODO: include in documentation
    df = df.replace("", np.nan)
    df_nans = np.where(pd.isnull(df))
    is_df_contains_nan = len(df_nans[0]) > 0
    if is_df_contains_nan:
        raise UploadError(
            "File contains empty cells. Remove them or fix them before resubmit."
        )

    # add all required columns
    df = _add_required_columns(df)

    state = {
        "data": from_df_to_db(df, add_index=True),
        "fields": df.dtypes.apply(lambda x: x.name).to_dict(),
    }

    return state


def _add_required_columns(df):
    for col in REQUIRED_COLUMNS:
        if not col in df.columns:
            df[col] = ""

    return df
