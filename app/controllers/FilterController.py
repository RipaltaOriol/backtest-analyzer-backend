import json
import os
from datetime import datetime, timedelta
from io import StringIO

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
