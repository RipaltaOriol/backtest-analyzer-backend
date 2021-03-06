import os
import json
from app import app
import numpy as np
import pandas as pd
from flask import jsonify, request
from flask.wrappers import Response
from flask_jwt_extended import get_jwt_identity

from app.models.User import User
from app.models.Setup import Setup
from app.models.Document import Document
from app.controllers.ErrorController import handle_403

""" Retrieves All Setups
"""
def get_setups():
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    setups = Setup.objects(author = user)
    response = []
    for setup in setups:
        current = setup.to_json()
        current = json.loads(current)
        options = get_filter_options(setup.documentId.id)
        current.update(options = options)
        response.append(current)
    response = json.dumps(response)
    return Response(response, mimetype = 'application/json')
    # return jsonify(response)
    # return jsonify([json.loads(setup.to_json()) for setup in setups])

""" Retrieves One Setup
    NOTE: no use - delete in future
"""
def get_setup(document_id, setup_id):
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(author = user, id = setup_id, documentId = document_id).get()
    # NOTE: second condition not necessary (ther is still some state in string formal: remove after) - it may still give errors
    if not setup.state:
        document = Document.objects(id = setup.documentId.id).get()
        # NOTE: this method probably needs improvement
        target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], document.path)
        df = pd.read_csv(target)
        df = df.to_json(orient = 'table')
        df = json.loads(df)
        setup.modify(state = df)

    response = setup.to_json()
    response = json.loads(response)
    # include filter options
    filter_options = get_filter_options(document_id)
    response.update(options = filter_options)
    response = json.dumps(response)
    return Response(response, mimetype = 'application/json')

""" Creates A New Setup
"""
def post_setup():
    id = get_jwt_identity()
    document = request.json.get('document', None)
    name = request.json.get('name', None)
    if name == '':
        name = 'undefined'
    # if not document ID is provided return error
    if not document:
        return handle_403(msg = 'Document is not provided')

    # NOTE check that doucment exists
    user = User.objects(id = id['$oid']).get()
    document = Document.objects(id = document).get()
    # save the setup to the DB
    setup = Setup(
        name = name,
        author = user,
        documentId = document,
        state = document.state,
        default = False
    ).save()

    return Response(setup.to_json(), mimetype = 'application/json')

""" Renames A Setup
"""
def put_setup(setup_id):
    id = get_jwt_identity()
    name = request.json.get('name', None)
    default = request.json.get('default', None)
    notes = request.json.get('notes', None)
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(id = setup_id, author = user).get()
    setup.name = name if name else setup.name
    setup.notes = notes if notes != None else setup.notes
    if default:
        Setup.objects(author = user, id__ne = setup_id, documentId = setup.documentId).update(default = False)
        setup.default = default
    setup.save()
    response = setup.to_json()
    response = json.loads(response)
    # loads options and appends them to setup
    options = get_filter_options(setup.documentId.id)
    response.update(options = options)
    response = json.dumps(response)
    return Response(response, mimetype = 'application/json')
    return jsonify({'msg': 'Setup successfully updated', 'success': True})

""" Delete A Setup
"""
def delete_setup(setup_id):
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    # get setup
    setup = Setup.objects(id = setup_id, author = user).get()
    setup.delete()
    return jsonify({'msg': 'Setup successfully deleted', 'success': True})

""" Gets Setup Statistics
"""
def get_statistics(setup_id):
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(author = user, id = setup_id).get()
    # transform DictField to JSON string for Pandas to read
    temp = json.dumps(setup.state)
    data = pd.read_json(temp, orient = 'table')
    statistics = []
    for column in data.columns:
        if column.startswith('.r_'):
            described = data[column].describe().apply("{0:.2f}".format).to_json()
            described = json.loads(described)
            # the prefix of ._r always has length 3
            described.update(name = column[3:])
            statistics.append(described)

    response = jsonify(statistics)
    return response

""" Get Setup Chart
    NOTE: needs some rethinking - probably move to different file
"""
def get_graphics(setup_id):
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(author = user, id = setup_id).get()
    temp = json.dumps(setup.state)
    data = pd.read_json(temp, orient = 'table')
    data.dropna(inplace = True)
    result_names = [column for column in data.columns if column.startswith('.r_')]

    # line chart
    equity = 1000
    datasets = []
    for column in result_names:
        points = []
        for i in range(len(data[column])):
            if i == 0:
                points.append(equity + equity * 0.01 * data['.r_Result'].iloc[i])
            else:
                points.append(points[i - 1] + points[i - 1] * 0.01 * data['.r_Result'].iloc[i])
        datasets.append({
            'name': column[3:],
            'values': points
        })

    line = {
        'name': '$' + str(equity) + ' Equity Simlutaion',
        'labels': list(range(1, 1 + len(data[result_names[0]]))),
        'datasets': datasets
    }

    # NOTE: this can be done more effiently
    pie = {
        'name': result_names[0][3:] + ' by Outcome Distribution',
        'labels': ['Winners', 'Break-Even', 'Lossers'],
        'values': [
            len(data[data[result_names[0]] > 0]),
            len(data[data[result_names[0]] == 0]),
            len(data[data[result_names[0]] < 0])
        ]
    }

    response = jsonify(line = line, pie = pie)
    return response

""" Gets Setup Filter Options
"""
def get_filter_options(doucment_id):
    document = Document.objects(id = doucment_id).get()
    temp = json.dumps(document.state)
    data = pd.read_json(temp, orient = 'table')

    map_types = data.dtypes
    options = []

    for column in data.columns:
        if column.startswith('.m_'):
            option = {
                "id": column,
                "name": column[3:]
            }
            if map_types[column] == 'float64' or map_types[column] == 'int64':
                option.update(type = 'number')
            else:
                option.update(type = 'string')
                option.update(values = list(data[column].dropna().unique()))
            options.append(option)
        if column.startswith('.p'):
            option = {
                "id": column,
                "name": column[2:],
                "type": "string",
                "values": list(data[column].dropna().unique())
            }
            options.append(option)

    return options