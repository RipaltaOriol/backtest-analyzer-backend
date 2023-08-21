import json
import os
import re
from io import StringIO

import numpy as np
import pandas as pd
from app import app
from app.controllers.ErrorController import handle_403
from app.controllers.GraphsController import get_bar, get_line, get_pie, get_scatter
from app.controllers.setup_utils import reset_state_from_document
from app.controllers.utils import from_db_to_df
from app.models.PPTTemplate import PPTTemplate
from app.models.Document import Document
from app.models.Setup import Setup
from app.models.User import User
from flask import jsonify, request
from flask.wrappers import Response
from app.controllers.RowController import update_ppt_row, update_default_row
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
    """Retrieves All Setups"""
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setups = Setup.objects(author=user)

    response = []
    for setup in setups:
        current = setup.to_json()
        current = json.loads(current)
        options = get_filter_options(setup.documentId.id)
        template = setup.documentId.template.name if setup.documentId.template else {}

        current.update(template=template)
        current.update(options=options)
        response.append(current)

    response = json.dumps(response, cls=CustomJSONizer)
    return Response(response, mimetype="application/json")
    # return jsonify(response)
    # return jsonify([json.loads(setup.to_json()) for setup in setups])


""" Retrieves One Setup
    NOTE: no use - delete in future
"""


def get_setup(document_id, setup_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id, documentId=document_id).get()
    # NOTE: second condition not necessary (ther is still some state in string formal: remove after) - it may still give errors
    if not setup.state:
        document = Document.objects(id=setup.documentId.id).get()
        # NOTE: this method probably needs improvement
        target = os.path.join(app.root_path, app.config["UPLOAD_FOLDER"], document.path)
        df = pd.read_csv(target)
        df = df.to_json(orient="table")
        df = json.loads(df)
        setup.modify(state=df)

    response = setup.to_json()
    response = json.loads(response)
    # include filter options
    filter_options = get_filter_options(document_id)
    response.update(options=filter_options)
    response = json.dumps(response)
    return Response(response, mimetype="application/json")


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


def get_setup_row(setup_id, row_id):

    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(id=setup_id).get()

    if not setup_id or not row_id:
        return {jsonify({"msg": "Something went wrong.", "success": False})}
    print(setup.state["data"][row_id]["col_p"])
    # return {"asset": setup.state["data"][row_id]["col_p"]}
    setup_row = PPTTemplate.objects(setup=setup_id, row_id=row_id)
    if setup_row:
        setup_row = setup_row.get()

    else:
        setup_row = PPTTemplate(
            author=user, document=setup.documentId, setup=setup, row_id=row_id
        ).save()

    response = json.loads(setup_row.to_json())
    response.update(success=True)
    return response


def put_setup_row(setup_id, row_id):
    """
    Updates a specific row in a setup. An options parameter is_sync can be passed so this update
    is reflected across all setups and the parent document itself.
    """
    row = request.json.get("row", None)
    note = request.json.get("note", None)
    images = request.json.get("images", [])
    # if sync is True then update the row on all Setups & Document
    is_sync = request.json.get("isSync", None)
    setup = Setup.objects(id=setup_id).get()
    if row_id == "undefined":
        return jsonify({"msg": "Something went wrong...", "success": False})
    setup = Setup.objects(id=setup_id).get()
    template_type = setup.documentId.template.name
    if template_type == "PPT":
        return update_ppt_row(setup, row_id, row)
    else:
        return update_default_row(setup, row_id, note, images, is_sync)


def get_statistics(setup_id):
    """
    Gets Setup Statistics
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()
    data = from_db_to_df(setup.state)
    result_columns = [col for col in data if re.match(r"col_[vpr]_", col)]

    count = {"stat": "Count"}
    total = {"stat": "Total"}
    mean = {"stat": "Mean"}
    wins = {"stat": "Wins"}
    losses = {"stat": "Losses"}
    break_even = {"stat": "Break Even"}
    win_rate = {"stat": "Win Rate"}
    avg_win = {"stat": "Average Win"}
    avg_loss = {"stat": "Average Loss"}
    expectancy = {"stat": "Expectancy"}
    max_consec_loss = {"stat": "Max. Consecutive Losses"}
    max_win = {"stat": "Maximum Win"}
    drawdown = {"stat": "Drawdown"}
    for col in result_columns:
        count[col] = 0
        total[col] = 0
        wins[col] = 0
        losses[col] = 0
        break_even[col] = 0
        total_wins = 0
        total_losses = 0
        consecutive_losses = 0
        current_losses = 0
        for val in data[col]:
            # TODO: add this when efficiently detecting misplaced values
            # skip NaN values
            # if pd.isna(val):
            #     continue
            count[col] += 1
            total[col] += val
            if val > 0:
                wins[col] += 1
                total_wins += val
                consecutive_losses = max(consecutive_losses, current_losses)
                current_losses = 0
            elif val < 0:
                total_losses += val
                losses[col] += 1
                current_losses += 1
            else:
                break_even[col] += 1
                consecutive_losses = max(consecutive_losses, current_losses)
                current_losses = 0
        data["cumulative"] = data[col].cumsum().round(2)
        data["high_value"] = data["cumulative"].cummax()
        data["drawdown"] = data["cumulative"] - data["high_value"]
        drawdown[col] = float(data["drawdown"].min())
        total[col] = round(total[col], 3)
        mean[col] = total[col] / count[col]
        win_rate[col] = wins[col] / count[col]
        avg_win[col] = total_wins / wins[col] if wins[col] else 0
        avg_loss[col] = total_losses / losses[col] if losses[col] else 0
        expectancy[col] = (win_rate[col] * avg_win[col]) - (
            (1 - win_rate[col]) * abs(avg_loss[col])
        )
        max_consec_loss[col] = max(consecutive_losses, current_losses)
        max_win[col] = float(data[col].max())

    statistics = [
        count,
        total,
        mean,
        wins,
        losses,
        break_even,
        win_rate,
        avg_win,
        avg_loss,
        expectancy,
        max_consec_loss,
        max_win,
        drawdown,
    ]
    response = jsonify(statistics)
    return response


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
    metric_columns = [col for col in data if col.startswith("col_m_")]

    if "col_rr" in data.columns:
        metric_columns.append("col_rr")

    # remove rows with not results recorded
    data.dropna(subset=result_columns, inplace=True)

    if type == "scatter":
        return get_scatter(data, result_columns, metric_columns, current_metric)
    if type == "bar":
        return get_bar(data, result_columns, metric_columns, current_metric)
    if type == "pie":
        return get_pie(data, result_columns)
    if type == "line":
        return get_line(data, result_columns, current_metric)
    return "Bad"


def get_filter_options(doucment_id):
    """
    Gets Setup Filter Options
    """
    document = Document.objects(id=doucment_id).get()

    data = from_db_to_df(document.state)

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

    return options


def update_setups(document_id):
    """
    Updates the setups state from parent state
    """
    setups = Setup.objects(documentId=document_id)
    for setup in setups:
        reset_state_from_document(setup.id)


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
