import json
import os
from io import StringIO

import numpy as np
import pandas as pd
from flask import jsonify, request
from flask.wrappers import Response

from app import app
from app.controllers.ErrorController import handle_403
from app.models.Document import Document
from app.models.Filter import Filter
from app.models.Setup import Setup

""" Applies a Filter to a dataframe
"""


def apply_filter(df, column, operation, value):
    print(column, operation, value)
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
            print("Come here")
            print(df[column])
            df = df[df[column] < value]
            print(df)
        elif operation == "eq":
            df = df[df[column] == value]
        elif operation == "ne":
            df = df[df[column] != value]
    return df


def reset_state_from_document(setup_id):

    setup = Setup.objects(id=setup_id).get()
    # establish remaining filters
    document = Document.objects(id=setup.documentId.id).get()

    temp = json.dumps(document.state)
    df = pd.read_json(StringIO(temp), orient="table")

    for filter in setup.filters:
        df = apply_filter(df, filter.column, filter.operation, filter.value)
    df = df.to_json(orient="table")
    df = json.loads(df)
    setup.modify(state=df)
