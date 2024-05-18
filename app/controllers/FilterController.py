import json
import logging
from datetime import datetime, timedelta
from io import StringIO
from typing import Union

import numpy as np
import pandas as pd
from app import app
from app.controllers.ErrorController import handle_403
from app.controllers.utils import from_db_to_df, from_df_to_db, retrieve_filter_options
from app.models.Document import Document
from app.models.Filter import Filter
from app.models.Setup import Setup
from bson import DBRef, ObjectId, json_util
from flask import jsonify, request
from flask.wrappers import Response


# Encoder to deal with numpy Boolean values
class CustomJSONizer(json.JSONEncoder):
    def default(self, obj):
        return (
            super().encode(bool(obj))
            if isinstance(obj, np.bool_)
            else super().default(obj)
        )


# TODO: this function can be improved
def apply_filter(df, column, operation, value):
    """
    Applies a Filter to a dataframe
    """
    if operation == "in" or operation == "nin":
        if df.dtypes[column] == "bool" and len(value) == 1:
            # convert string 'true' or 'false' to bool
            value_bool = value[0] == "true"
            if operation == "in":
                df = df[df[column] == value_bool]
            elif operation == "nin":
                df = df[df[column] != value_bool]
        elif column == "col_d":
            if operation == "in":
                df = df[df[column].str.fullmatch("|".join(value), case=False)]
            elif operation == "nin":
                df = df[-df[column].str.fullmatch("|".join(value), case=False)]
        else:
            if operation == "in":
                df = df[df[column].isin(value)]
            elif operation == "nin":
                df = df[-df[column].isin(value)]

    elif operation == "date":
        date_from = datetime.strptime(value[0], "%m/%d/%Y").strftime("%Y-%m-%d")
        date_to = datetime.strptime(value[1], "%m/%d/%Y") + timedelta(days=1)
        date_to = date_to.strftime("%Y-%m-%d")
        df = df.loc[(df[column] >= date_from) & (df[column] < date_to)]

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


def get_filter_options(doucment_id):
    """
    Gets Setup Filter Options
    """
    document = Document.objects(id=doucment_id).get()

    data = from_db_to_df(document.state)
    data.replace({np.nan: None}, inplace=True)

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
        if column.startswith("col_p"):
            option = {
                "id": column,
                "name": "Pair",
                "type": "string",
                "values": list(data[column].dropna().unique()),
            }
            options.append(option)
        if column.startswith("col_rr"):
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

    return options


def get_filter_name(column, operation, value):
    """
    Generates filter name
    """
    # initialise the name variable
    name = ""
    # get the column
    if column.startswith("col_p"):
        name += "Pair"
    elif column.startswith("col_rr"):
        name += "Risk Reward"
    else:
        name += column[6:]
    if operation == "gt":
        name += " greater than "
    elif operation == "lt":
        name += " lesser than "
    elif operation == "eq":
        name += " equal to "
    elif operation == "ne":
        name += " not equal to "
    elif operation == "in":
        name += " includes "
    elif operation == "nin":
        name += " not includes "

    # special format for dates
    if operation == "date":
        name += f" from {value[0]} to {value[1]}"
    else:
        # attach values
        values = ", ".join(str(v) for v in value)
        name += values
    return name


def post_filter(setup_id: str):
    """
    Adds a Filter to a Setup
    """
    column = request.json.get("column", None)
    operation = request.json.get("action", None)
    value = request.json.get("value", None)
    setup = Setup.objects(id=setup_id).first()
    df = from_db_to_df(setup.state)
    if column == None or operation == None or value == None:
        return handle_403(msg="Filter is not valid")

    df = apply_filter(df, column, operation, value)
    name = get_filter_name(column, operation, value)
    data = from_df_to_db(df)

    filter = Filter(
        name=name,
        column=column,
        operation=operation,
        value=value,
    ).save()

    is_updated = setup.modify(push__filters=filter, set__state__data=data)

    if is_updated:
        updated_setup = Setup.objects(id=setup_id).aggregate(
            [
                {
                    "$lookup": {
                        "from": Document._get_collection_name(),
                        "localField": "documentId",
                        "foreignField": "_id",
                        "as": "document",
                    },
                },
                {
                    "$lookup": {
                        "from": Filter._get_collection_name(),
                        "localField": "filters",
                        "foreignField": "_id",
                        "as": "filters",
                    },
                },
                {
                    "$addFields": {
                        "filters": {
                            "$map": {
                                "input": "$filters",
                                "as": "filter",
                                "in": {
                                    "$mergeObjects": [
                                        "$$filter",
                                        {"id": {"$toString": "$$filter._id"}},
                                    ]
                                },
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "id": {"$toString": "_id"},
                        "default": 1,
                        "filters.id": 1,
                        "filters.name": 1,
                        "documentId": {"$toString": "documentId"},
                        "state": 1,
                        "notes": 1,
                        "name": 1,
                        "date_created": {
                            "$dateToString": {
                                "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                                "date": {"$toDate": "$date_created"},
                            }
                        },
                        "document.state": 1,
                    }
                },
            ]
        )

        updated_setup = json.loads(json_util.dumps(updated_setup))[0]

        df = from_db_to_df(updated_setup["document"][0]["state"])
        updated_setup["options"] = retrieve_filter_options(df)

        del updated_setup["document"]

        return jsonify(updated_setup)


def delete_filter(setup_id, filter_id):
    """
    Deletes a filter in a Setup. It first looks up the Filter and Setup. It deletes the Filter from the Setup and
    restores its state from parent (Document). After, deletes the Filter from the database. Lastly, it returns the Setup.

    TODO: I believe this function can be optimized
    """
    try:
        setup = Setup.objects(id=setup_id).first()
        filter_dlt = Filter.objects(id=filter_id).first()
        # delete filter instance in setup
        to_dlt = filter_dlt.pk
        setup.modify(pull__filters=to_dlt)

        # establish remaining filters
        document = Document.objects(id=setup.documentId.id).get()
        df = from_db_to_df(document.state)

        for filter in setup.filters:
            df = apply_filter(df, filter.column, filter.operation, filter.value)

        data = from_df_to_db(df)
        setup.modify(set__state__data=data)

        # delete filter
        filter_dlt.delete()

        response = setup.to_json()
        response = json.loads(response)
        # loads options and appends them to setup
        options = get_filter_options(setup.documentId.id)
        response.update(options=options)
        response = json.dumps(response, cls=CustomJSONizer)

        return Response(response, mimetype="application/json")

    except:
        return handle_403(msg="Somethign went wrong")


# TODO: this will need some rework and heavy testing
def filter_open_trades(
    df: pd.DataFrame,
    column: str,
    column_type: str,
    operation: str,
    value: Union[float, int, str],
):
    """
    Filters a DataFrame based on a specified operation applied to a given column.
    This function supports a variety of operations such as checking for empty/non-empty
    values, equality, numeric comparisons, and datetime comparisons.

    Parameters:
    - df (pd.DataFrame): The DataFrame to be filtered.
    - column (str): The name of the column in the DataFrame to apply the filter on.
    - operation (str): The operation to perform. Supported operations include
      "empty", "not_empty", "equal", "not_equal", "higher", "lower",
      "before" (for datetime), and "after" (for datetime).
    - value (str or int): The value to compare against for "equal", "not_equal",
      "higher", "lower", "before", and "after" operations. Its type should
      match the type of the column being compared. Default is None.
    - column_type (str): The data type of the column, which can be "object",
      "float64", "int64", or start with "datetime64". It is particularly necessary
      for datetime comparisons. Default is None.

    Returns:
    pd.DataFrame: A DataFrame filtered based on the specified operation and conditions.

    Raises:
    - ValueError: If an unsupported operation is provided.

    """
    try:
        # Handle 'empty' and 'not_empty' operations directly
        if operation == "empty":
            return df[df[column].isna() | (df[column] == "")]
        elif operation == "not_empty":
            return df[df[column].notna() & (df[column] != "")]

        # Operations based on column_type
        if column_type in ["object", "float64", "int64"]:
            # Parse value as number if data type is a number
            value = float(value) if column_type in ["float64", "int64"] else value
            if operation == "equal":
                return df[df[column] == value]
            elif operation == "not_equal":
                return df[df[column] != value]
            elif column_type in ["float64", "int64"]:  # Numeric comparisons
                if operation == "higher":
                    return df[df[column] > value]
                elif operation == "lower":
                    return df[df[column] < value]

        elif column_type.startswith("datetime64"):
            # Convert value to datetime format expected by pandas
            date_value = datetime.strptime(value, "%m/%d/%Y").strftime("%Y-%m-%d")
            if operation == "before":
                return df[df[column] < date_value]
            elif operation == "after":
                return df[df[column] > date_value]

        raise ValueError(
            "No filter match for column was achieved. Review condition for open positions."
        )
    except Exception as error:
        logging.error(f"Error on filtering for open trades: {str(error)}")
        raise ValueError(str(error))
