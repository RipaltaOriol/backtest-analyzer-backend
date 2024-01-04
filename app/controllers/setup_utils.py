import json
import os
from io import StringIO

import numpy as np
import pandas as pd
from app import app
from app.controllers.ErrorController import handle_403
from app.controllers.utils import from_db_to_df, from_df_to_db
from app.models.Document import Document
from app.models.Filter import Filter
from app.models.Setup import Setup
from flask import jsonify, request
from flask.wrappers import Response

""" Applies a Filter to a dataframe
"""


def apply_filter(df, column, operation, value):
    if operation == "in" or operation == "nin":
        if df.dtypes[column] == "bool" and len(value) == 1:
            # convert string 'true' or 'false' to bool
            value_bool = value[0] == "true"
            if operation == "in":
                df = df[df[column] == value_bool]
            elif operation == "nin":
                df = df[df[column] != value_bool]
        else:
            if operation == "in":
                df = df[df[column].isin(value)]
            elif operation == "nin":
                df = df[-df[column].isin(value)]
    else:
        # update the value so that it only gets the first element
        value = value[0]
        if operation == "gt":
            df = df[df[column] > value]
        elif operation == "lt":
            df = df[df[column] < value]
        elif operation == "eq":
            df = df[df[column] == value]
        elif operation == "ne":
            df = df[df[column] != value]
    return df
