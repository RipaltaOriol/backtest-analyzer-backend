import json
import os
from io import StringIO

import numpy as np
import pandas as pd
from app import app
from app.controllers.ErrorController import handle_403
from app.controllers.GraphsController import get_bar, get_pie, get_scatter
from app.controllers.setup_utils import reset_state_from_document
from app.models.Document import Document
from app.models.Setup import Setup
from app.models.User import User
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


""" Retrieves All Setups
"""


def get_setups():
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setups = Setup.objects(author=user)

    response = []
    for setup in setups:
        current = setup.to_json()
        current = json.loads(current)
        options = get_filter_options(setup.documentId.id)
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


""" Creates A New Setup
"""


def post_setup():
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


""" Renames A Setup
"""


def put_setup(setup_id):
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


""" Delete A Setup
"""


def delete_setup(setup_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get setup
    setup = Setup.objects(id=setup_id, author=user).get()

    for filter in setup.filters:
        filter.delete()
    setup.delete()
    return jsonify({"msg": "Setup successfully deleted", "success": True})


""" Gets Setup Statistics
"""


def get_statistics(setup_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()
    # transform DictField to JSON string for Pandas to read
    temp = json.dumps(setup.state)
    data = pd.read_json(StringIO(temp), orient="table")
    result_columns = [col for col in data if col.startswith(".r_")]

    count = {"stat": "Count"}
    total = {"stat": "Total"}
    wins = {"stat": "Wins"}
    losses = {"stat": "Losses"}
    break_even = {"stat": "Break Even"}
    win_rate = {"stat": "Win Rate"}
    avg_win = {"stat": "Average Win"}
    avg_loss = {"stat": "Average Loss"}
    expectancy = {"stat": "Expectancy"}
    max_consec_loss = {"stat": "Max. Consecutive Losses"}
    max_win = {"stat": "Maximum Win"}

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
        total[col] = round(total[col], 3)
        win_rate[col] = wins[col] / count[col]
        avg_win[col] = total_wins / wins[col] if wins[col] else 0
        avg_loss[col] = total_losses / losses[col] if losses[col] else 0
        expectancy[col] = (win_rate[col] * avg_win[col]) - (
            (1 - win_rate[col]) * abs(avg_loss[col])
        )
        max_consec_loss[col] = max(consecutive_losses, current_losses)
        max_win[col] = data[col].max()

    statistics = [
        count,
        total,
        wins,
        losses,
        break_even,
        win_rate,
        avg_win,
        avg_loss,
        expectancy,
        max_consec_loss,
        max_win,
    ]

    response = jsonify(statistics)
    return response


""" Get Setup Chart
    NOTE: needs some rethinking - probably move to different file
    NOTE: think of a method for data sanitization to drop NaN values so it does not break 
"""


def get_graphics(setup_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()
    temp = json.dumps(setup.state)
    data = pd.read_json(StringIO(temp), orient="table")
    # data.dropna(inplace = True)
    result_names = [column for column in data.columns if column.startswith(".r_")]

    # line chart
    datasets = []
    for column in result_names:
        equity = 1000
        points = []
        for i in range(len(data[column])):
            if i == 0:
                points.append(equity + equity * 0.01 * data[column].iloc[i])
            else:
                points.append(
                    points[i - 1] + points[i - 1] * 0.01 * data[column].iloc[i]
                )
        datasets.append({"name": column[3:], "values": points})

    line = {
        "name": "$" + str(equity) + " Equity Simlutaion",
        "labels": list(range(1, 1 + len(data[result_names[0]]))),
        "datasets": datasets,
    }

    # NOTE: this can be done more effiently
    pie = {
        "name": result_names[0][3:] + " by Outcome Distribution",
        "labels": ["Winners", "Break-Even", "Lossers"],
        "values": [
            len(data[data[result_names[0]] > 0]),
            len(data[data[result_names[0]] == 0]),
            len(data[data[result_names[0]] < 0]),
        ],
    }

    response = jsonify(line=line, pie=pie)
    return response


""" Gets Setups Graphs
"""


def get_graphs(setup_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    setup = Setup.objects(author=user, id=setup_id).get()
    temp = json.dumps(setup.state)
    data = pd.read_json(StringIO(temp), orient="table")
    # data.dropna(inplace = True)
    args = request.args
    type = args.get("type")

    if not type:
        # throw exeption
        return "Bad"

    result_columns = [column for column in data.columns if column.startswith(".r_")]
    metric_columns = [col for col in data if col.startswith(".m_")]

    if type == "scatter":
        return get_scatter(data, result_columns, metric_columns)
    if type == "bar":
        return get_bar(data, result_columns, metric_columns)
    if type == "pie":
        return get_pie(data, result_columns)
    return "Bad"


""" Gets Setup Filter Options
"""


def get_filter_options(doucment_id):
    document = Document.objects(id=doucment_id).get()
    temp = json.dumps(document.state)

    # newdf = pd.read_json(StringIO(temp))
    data = pd.read_json(StringIO(temp), orient="table")
    # return 'Hello'

    map_types = data.dtypes
    options = []
    for column in data.columns:
        if column.startswith(".m_"):
            option = {"id": column, "name": column[3:]}
            if map_types[column] == "float64" or map_types[column] == "int64":
                option.update(type="number")
            else:
                option.update(type="string")
                option.update(values=list(data[column].dropna().unique()))
            options.append(option)
        if column.startswith(".p"):
            option = {
                "id": column,
                "name": "Pair",
                "type": "string",
                "values": list(data[column].dropna().unique()),
            }
            options.append(option)

    return options


""" Updates the setups state from parent state
"""


def update_setups(document_id):
    setups = Setup.objects(documentId=document_id)
    for setup in setups:
        reset_state_from_document(setup.id)


def get_children(document_id):
    setups = Setup.objects(documentId=document_id).order_by("-date_created")
    return [
        {"id": str(setup.id), "name": setup.name, "date": setup.date_created}
        for setup in setups
    ]
