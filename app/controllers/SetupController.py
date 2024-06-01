import datetime
import json
import math
import os
import re
from io import StringIO

import numpy as np
import pandas as pd
from app import app
from app.controllers.db_pipelines.template_pipelines import get_ppt_template_row
from app.controllers.ErrorController import handle_403
from app.controllers.FilterController import (
    apply_filter,
    filter_open_trades,
    get_filter_options,
)
from app.controllers.GraphsController import get_bar, get_line, get_pie, get_scatter
from app.controllers.RowController import update_default_row, update_ppt_row
from app.controllers.utils import (
    from_db_to_df,
    from_df_to_db,
    get_result_decorator,
    normalize_results,
    parse_column_name,
    retrieve_filter_options,
)
from app.models.Document import Document
from app.models.Filter import Filter
from app.models.PPTTemplate import PPTTemplate
from app.models.Setup import Setup
from app.models.Template import Template
from app.models.User import User
from app.repositories.user_repository import UserRepository
from app.repositories.version_repository import VersionRepository
from app.services.statistics_service import StatisticsService
from app.services.version_service import VersionService
from app.utils.encoders import NpEncoder
from bson import DBRef, ObjectId, json_util
from flask import jsonify, request
from flask.wrappers import Response
from flask_jwt_extended import get_jwt_identity


# Encoder to deal with numpy Boolean values
class CustomJSONizer(json.JSONEncoder):
    def default(self, obj):
        return (
            super().encode(bool(obj))
            if isinstance(obj, np.bool_)
            else super().default(obj)
        )


def get_setups():
    """
    Retrieves All Setups for a given User

    TODO: this query in the main one to be called by the app. It should be optimized as much
    as possible. Here are some suggestions for small improvements.

    https://stackoverflow.com/questions/16586180/typeerror-objectid-is-not-json-serializable (JSONEncoder)
    https://stackoverflow.com/questions/30333299/pymongo-bson-convert-python-cursor-cursor-object-to-serializable-json-object
    (using bsonjs)
    """
    id = get_jwt_identity()

    pipeline = [
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
                "from": Template._get_collection_name(),
                "localField": "document.template",
                "foreignField": "_id",
                "as": "template",
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
        {"$sort": {"document._id": -1}},
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "notes": 1,
                "default": 1,
                "template.name": 1,
                "state": 1,
                "date_created": {"$dateToString": {"date": "$date_created"}},
                "document.state": 1,
                "document._id": 1,
                "filters.id": 1,
                "filters.name": 1,
            }
        },
    ]

    setups = Setup.objects(author=id["$oid"]).aggregate(pipeline)

    setups = json.loads(json_util.dumps(setups))

    df = None
    document_id = None

    for setup in setups:

        setup["id"] = setup["_id"]["$oid"]
        # setup["date_created"] = setup["date_created"].isoformat()
        document = setup["document"][0]
        setup["documentId"] = document["_id"]["$oid"]

        if not setup["documentId"] == document_id or not isinstance(df, pd.DataFrame):
            df = from_db_to_df(document["state"])
            document_id = setup["documentId"]

        setup["template"] = setup["template"][0]["name"] if setup["template"] else None
        setup["options"] = retrieve_filter_options(df)

        del setup["_id"]
        del setup["document"]

    return jsonify(setups)


def post_setup():
    """
    Creates A New Setup
    """
    id = get_jwt_identity()
    document = request.json.get("document", None)
    name = request.json.get("name", None)
    if name == "":
        name = "undefined"
    # if not document ID is provided return error
    if not document:
        return handle_403(msg="Document is not provided")

    # NOTE check that doucment exists
    user = User.objects(id=id["$oid"]).get()
    document = Document.objects(id=document).get()
    # save the setup to the DB
    setup = Setup(
        name=name, author=user, documentId=document, state=document.state, default=False
    ).save()

    return Response(setup.to_json(), mimetype="application/json")


def put_setup(setup_id):
    """
    Renames A Setup
    """
    id = get_jwt_identity()
    name = request.json.get("name", None)
    default = request.json.get("default", None)
    notes = request.json.get("notes", None)
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(id=setup_id, author=user).get()
    setup.name = name if name else setup.name
    setup.notes = notes if notes != None else setup.notes
    if default:
        Setup.objects(author=user, id__ne=setup_id, documentId=setup.documentId).update(
            default=False
        )
        setup.default = default
    setup.save()
    response = setup.to_json()
    response = json.loads(response)
    # loads options and appends them to setup
    options = get_filter_options(setup.documentId.id)
    response.update(options=options)
    response = json.dumps(response)
    return Response(response, mimetype="application/json")
    return jsonify({"msg": "Setup successfully updated", "success": True})


def delete_setup(setup_id):
    """
    Delete one Setup
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get setup
    setup = Setup.objects(id=setup_id, author=user).get()

    for filter in setup.filters:
        filter.delete()
    setup.delete()
    return jsonify({"msg": "Setup successfully deleted", "success": True})


def get_setup_row(document_id, row_id):
    """
    NOTE: replace this at another location
    It takes in a document_id and row_id and returns the matching row object in JSON format.
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    document = Document.objects(id=document_id).get()

    if not document_id or not row_id:
        return {jsonify({"msg": "Something went wrong.", "success": False})}
    # return {"asset": setup.state["data"][row_id]["col_p"]}

    row = PPTTemplate.objects(document=document_id, row_id=row_id)
    if not row:
        # NOTE: make a funciton to create an empty one
        # NOTE: I do not know if this works tbh!!!
        row = PPTTemplate(author=user, document=document, row_id=row_id).save()

    # row.aggregate(pipeline2)
    try:
        query = next(row.aggregate(get_ppt_template_row))
        response = json.loads(json_util.dumps(query))
        return response

    except StopIteration:
        print("Document not found.")
        return {jsonify({"msg": "Something went wrong.", "success": False})}


def put_setup_row(setup_id, row_id):
    """
    Updates a specific row in a setup. An options parameter is_sync can be passed so this update
    is reflected across all setups and the parent document itself.
    """
    row = request.json.get("row", None)
    note = request.json.get("note", None)
    images = request.json.get("images", [])
    # TODO: remove logic for sync
    # if sync is True then update the row on all Setups & Document
    is_sync = request.json.get("isSync", None)
    # setup = Setup.objects(id=setup_id).get()
    document = Document.objects(id=setup_id).get()
    if row_id == "undefined":
        return jsonify({"msg": "Something went wrong...", "success": False})
    template_type = document.template.name
    if template_type == "PPT":
        return update_ppt_row(document, row_id, row)
    else:
        return update_default_row(document, row_id, note, images, is_sync)


def get_statistics(setup_id):
    """
    Gets Setup Statistics
    """
    version_repository = VersionRepository()
    version = version_repository.get_version_by_id(setup_id)
    version_df = version_repository.get_version_dataframe(version)
    stats_service = StatisticsService()
    statistics, error = stats_service.get_dataframe_statistics(version_df)

    if error:
        return jsonify({"success": False, "msg": error}), 400

    response = {
        "data": statistics,
        "success": True,
    }
    response = json.dumps(response, cls=NpEncoder)
    return Response(response, mimetype="application/json")


def get_graphics(setup_id):
    """
    Get Setup Chart
    NOTE: needs some rethinking - probably move to different file
    NOTE: think of a method for data sanitization to drop NaN values so it does not break
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()
    data = from_db_to_df(setup.state)

    # data.dropna(inplace = True)
    result_names = [
        column for column in data.columns if re.match(r"col_[vpr]_", column)
    ]

    if not result_names:
        return jsonify(success=False, msg="No available data yet")

    # NOTE: this can be done more effiently
    pie = {
        "name": result_names[0][6:] + " by Outcome Distribution",
        "labels": ["Winners", "Break-Even", "Lossers"],
        "values": [
            len(data[data[result_names[0]] > 0]),
            len(data[data[result_names[0]] == 0]),
            len(data[data[result_names[0]] < 0]),
        ],
    }

    response = jsonify(pie=pie, success=True)
    return response


def get_graphs(setup_id):
    """
    Gets Setups Graphs
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()
    data = from_db_to_df(setup.state)
    # data.dropna(inplace = True)
    args = request.args
    type = args.get("type")
    current_metric = args.get("currentMetric")
    if not type:
        # throw exeption
        return "Bad"

    result_columns = [
        column for column in data.columns if re.match(r"col_[vpr]_", column)
    ]

    metric_columns = {
        k: v
        for k, v in setup.state["fields"].items()
        if k == "col_rr" or k == "col_p" or k.startswith("col_m_")
    }

    # remove rows with no results recorded
    # data.dropna(subset=result_columns, inplace=True) # handle this
    data.replace({np.nan: None}, inplace=True)

    if type == "scatter":
        return get_scatter(data, result_columns, metric_columns, current_metric)
    if type == "bar":
        return get_bar(data, result_columns, metric_columns, current_metric)
    if type == "pie":
        return get_pie(data, result_columns)
    if type == "line":
        return get_line(data, result_columns, current_metric)
    return "Bad"


def update_setups(
    document_id,
    document_df: pd.DataFrame,
    document_fields=None,
    wiht_fields=False,
    remove_filters=False,
) -> None:
    """
    Updates the setups state from parent state
    """
    df = document_df
    setups = Setup.objects(documentId=document_id)

    for setup in setups:
        filtered_df = df
        if remove_filters:
            setup.modify(__raw__={"$set": {"filters": []}})
        else:
            for filter in setup.filters:
                filtered_df = apply_filter(
                    filtered_df, filter.column, filter.operation, filter.value
                )
        data = from_df_to_db(filtered_df)
        if wiht_fields:
            setup.modify(
                __raw__={"$set": {"state": {"fields": document_fields, "data": data}}}
            )
        else:
            setup.modify(__raw__={"$set": {"state.data": data}})


def get_children(document_id):
    setups = Setup.objects(documentId=document_id).order_by("-date_created")
    return [
        {
            "id": str(setup.id),
            "name": setup.name,
            "date": setup.date_created,
            "isDefault": setup.default,
        }
        for setup in setups
    ]


# TODO: move this to its own route setup/id/stats/{stats_id}
def get_daily_distribution(setup_id):
    """
    Get daily distribution for setup
    """
    id = get_jwt_identity()

    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()
    df = from_db_to_df(setup.state)
    date_columns = [column for column in df.columns if re.match(r"col_d_", column)]
    result_columns = [
        column for column in df.columns if re.match(r"col_[vpr]_", column)
    ]
    if not date_columns or not result_columns:
        return jsonify(
            {
                "success": False,
                "message": "No date or result data found in this account.",
            }
        )

    week_df = df.groupby(df[date_columns[0]].dt.day_name()).mean(numeric_only=True)

    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    response = {}

    for col in result_columns:
        weekday_mean = {}
        for day in weekdays:

            mean = 0

            if day in week_df.index:
                if np.isnan(week_df.loc[day, col]):
                    mean = None
                else:
                    mean = round(week_df.loc[day, col], 3)
            else:
                mean = 0

            weekday_mean[day] = mean
            result_column = parse_column_name(col)
        response[result_column] = weekday_mean
    return jsonify({"success": True, "data": response})


# TODO: move this to its own route setup/id/stats/{stats_id}
def get_net_results(setup_id):
    """
    Get net returns from a setup
    # TODO: might have to take in account order (for now it is not an issue)
    """
    id = get_jwt_identity()

    user = User.objects(id=id["$oid"]).get()

    setup = Setup.objects(author=user, id=setup_id).get()
    df = from_db_to_df(setup.state)

    result_columns = [
        column for column in df.columns if re.match(r"col_[vpr]_", column)
    ]

    # TODO: it should be able to adjustabble by metrics
    if not result_columns:
        return jsonify(
            {"success": False, "message": "No results data found in this account."}
        )

    data = {}
    for column in result_columns:
        data[column] = df[column].replace({np.nan: None}).tolist()

    result = {"success": True, "labels": list(range(1, len(df.index))), "data": data}

    return jsonify(result)


# TODO: move this to its own route setup/id/stats/{stats_id}
def get_cumulative_results(setup_id):
    """
    Get cumulative returns from a setup
    # TODO: might have to take in account order (for now it is not an issue)
    """

    id = get_jwt_identity()

    user = User.objects(id=id["$oid"]).get()

    setup = Setup.objects(author=user, id=setup_id).get()
    df = from_db_to_df(setup.state)

    result_columns = [
        column for column in df.columns if re.match(r"col_[vpr]_", column)
    ]

    # TODO: it should be able to adjustabble by metrics
    if not result_columns:
        return jsonify(
            {"success": False, "message": "No results data found in this account."}
        )

    data = {}
    for column in result_columns:
        data[column] = df[column].cumsum().replace({np.nan: None}).tolist()

    result = {
        "success": True,
        "labels": list(range(1, len(df.index) + 1)),
        "data": data,
    }

    return jsonify(result)


# TODO: move this to its own route setup/id/stats/{stats_id}
def get_bubble_results(setup_id):
    """
    ....
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()

    args = request.args
    current_metric = args.get("currentMetric")

    df = from_db_to_df(setup.state)
    df.replace({np.nan: None}, inplace=True)

    data = []
    metric_list = [
        col
        for col, dtype in setup.state["fields"].items()
        if col.startswith("col_m_") and (dtype == "int64" or dtype == "float64")
    ]
    result_columns = [
        column for column in df.columns if re.match(r"col_[vpr]_", column)
    ]

    if len(result_columns) == 0 or len(metric_list) == 0:
        return jsonify(
            {
                "success": False,
                "msg": "Not enough data to compute",
            }
        )

    if "col_rr" not in df.columns:
        return jsonify(
            {
                "success": False,
                "msg": "Risk Reward was not found on this account.",
            }
        )

    metric_num = None

    if current_metric in metric_list:
        metric_num = current_metric
    else:
        metric_num = metric_list[0]

    if metric_num == None:
        return "Bad"

    for res in result_columns:
        dataset = {
            "label": res[6:],
        }
        dataset_data = []
        for i in df.index:
            result_point = df.loc[i, res]
            metric_point = df.loc[i, metric_num]
            rrr_point = df.loc[i, "col_rr"]
            if (
                result_point is not None
                and metric_point is not None
                and rrr_point is not None
            ):  # check also the RRR
                dataset_data.append(
                    {
                        "x": round(float(metric_point), 3),
                        "y": round(float(normalize_results(result_point, res)), 3),
                        "r": round(rrr_point * 5, 3),
                    }
                )
        dataset["data"] = dataset_data
        data.append(dataset)

    labels = {
        "title": f"{parse_column_name(metric_num)} to Results and RRR",
        "axes": parse_column_name(metric_num),
    }

    return jsonify(
        {
            "success": True,
            "data": data,
            "labels": labels,
            "active_metric": metric_num,
            "metric_list": [
                [metric, parse_column_name(metric)] for metric in metric_list
            ],
        }
    )


def get_calendar_table(setup_id):
    """
    Returns a calendar view for a given setup.
    As well as options and selected metric for result and date display.
    """
    metric = request.args.get("metric", None)
    date = request.args.get("date", None)
    setup = Setup.objects(id=setup_id).get()
    df = from_db_to_df(setup.state, orient="index")
    # TODO: combine both loops into a single
    metric_list = [col for col in df if re.match(r"col_[vpr]_", col)]
    # TODO: is it col_r or col_r_
    date_list = [col for col in df if col.startswith("col_d_")]
    if not date_list or not metric_list:
        return jsonify(
            {"success": False, "msg": "Account does not contain any date information."}
        )

    metric = metric_list[0] if metric is None or metric not in metric_list else metric
    date = date_list[0] if date is None or date not in date_list else date
    # Reset index to get the index column passed in to the JSON
    table = df.reset_index(names="rowId").to_json(orient="records", date_format="iso")
    table = json.loads(table)
    response = {
        "success": True,
        "table": table,
        "metrics": [[metric, parse_column_name(metric)] for metric in metric_list],
        "active_metric": metric,
        "active_date": date,
        "dates": [[date, parse_column_name(date)] for date in date_list],
    }

    response = jsonify(response)
    return response


def get_calendar_statistics(version_id) -> Response:
    """
    Returns statistics on the version performance for the given month and year,
    with optional timezone offset adjustments.
    """
    metric_column = request.args.get("metric", None)
    date_column = request.args.get("date", None)
    calendar_month_year = request.args.get("monthYear", None)
    timezone_offset = request.args.get("offset", default=0, type=int)

    if not all([metric_column, date_column, calendar_month_year]):
        return jsonify({"success": False, "msg": "Required parameters are missing."})

    try:
        month, year = map(int, calendar_month_year.split("/"))
    except ValueError:
        return jsonify(
            {"success": False, "msg": "Invalid monthYear format. Use MM/YYYY format."}
        )

    # TODO: UPDATE THIS AND REGULAR STATISTICS
    version_service = VersionRepository()

    version = version_service.get_version_by_id(version_id)

    version_df = version_service.get_version_dataframe(version)
    version_columns = version_service.get_version_columns(version)

    if metric_column not in version_columns or date_column not in version_columns:
        return jsonify({"success": False, "msg": "Invalid metric or date selected."})

    stats_service = StatisticsService()
    result, error = stats_service.get_calendar_statistics(
        version_df, date_column, metric_column, month, year, timezone_offset
    )

    if error:
        return jsonify({"success": False, "msg": error})

    response = json.dumps(result, cls=NpEncoder)
    return Response(response, mimetype="application/json")


def get_open_trades(version_id) -> Response:
    """
    Fetches open trades based on predefined conditions in a document associated with a given version ID.

    This function retrieves a specific setup version by its ID, then fetches the associated document to obtain the first open condition. It applies this condition to filter trades from the version's state, which is converted to a DataFrame for processing. The function returns the filtered trades in a structured JSON format, indicating successful operation, or returns an error message in case of failure.

    Parameters:
    - version_id (str): The unique identifier of the setup version from which to fetch open trades.

    Returns:
    - Flask.Response: A Flask JSON response object containing either:
        a) A success response with "openTrades" key holding the filtered open trades and a "success" flag set to True.
        b) An error response with "message" key detailing the exception encountered and a "success" flag set to False.

    Raises:
    - Exception: Catches and handles any exception that occurs during the process, returning a structured error message. Specific exceptions can be handled and logged for debugging purposes.
    """
    # TODO: fetch related documents in a more direct and efficient way if possible.
    # version = Setup.objects(id=version_id).select_related('documentId').get()

    version = Setup.objects(id=version_id).get()
    account = Document.objects(id=version.documentId.id).get()

    # check if condition is set
    if not account.open_conditions:
        return jsonify(
            {
                "openTrades": {},
                "success": True,
            }
        )

    # Directly access the first open_condition from the account to avoid multiple accesses.
    column = account.open_conditions[0].column
    condition = account.open_conditions[0].condition
    value = account.open_conditions[0].value
    column_type = account.state["fields"].get(column)

    # Convert the database state to a DataFrame once to avoid redundant conversions.
    df = from_db_to_df(version.state)

    try:
        # Filter the DataFrame based on the open trades criteria.
        open_trades = filter_open_trades(df, column, column_type, condition, value)
        return jsonify(
            {
                "openTrades": from_df_to_db(open_trades),
                "success": True,
            }
        )

    except Exception as error:
        # TODO: consider logging the error here.
        return jsonify(
            {
                "message": str(error),
                "success": False,
            }
        )


def get_version_note(version_id) -> json:
    version_service = VersionService()
    version_note = version_service.get_version_note(version_id)
    return jsonify({"note": version_note, "success": True})


def put_version_note(version_id) -> json:
    notes = request.json.get("notes", None)
    is_success = False
    if notes:
        version_service = VersionService()
        version_service.put_version_note(version_id, {"notes": notes})
        is_success = True
    return jsonify({"success": is_success})
