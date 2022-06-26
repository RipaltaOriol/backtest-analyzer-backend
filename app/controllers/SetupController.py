import os
import json
from app import app
import pandas as pd
from flask import jsonify, request
from flask.wrappers import Response
from flask_jwt_extended import get_jwt_identity

from app.models.User import User
from app.models.Setup import Setup
from app.models.Document import Document

""" Retrieves All Setups
"""
def get_setups(document_id):
    id = get_jwt_identity()
    setups = []
    user = User.objects(id = id['$oid']).get()
    files = Setup.objects(author = user, documentId = document_id)

    for file in files:
        setup = {
            'id': str(file.id),
            'name': file.name,
            'date': file.date_created,
            'default': file.default
        }
        setups.append(setup)
    response = jsonify(setups)
    return response

""" Retrieves One Setup
"""
def get_setup(document_id, setup_id):
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(author = user, id = setup_id, documentId = document_id).get()
    if setup.state == None:
        document = Document.objects(id = setup.documentId.id).get()
        # NOTE: this method probably needs improvement
        target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], document.path)
        df = pd.read_csv(target)
        df = df.to_json(orient = 'split')
        setup.modify(state = df)
    response = setup.to_json()
    response = json.loads(response)
    # include filter options
    filter_options = get_filter_options(document_id)
    response.update(options = filter_options)
    response = jsonify(response)

    return response
    # return Response(response, mimetype = 'application/json')

""" Creates A New Setup
    NOTE: fix issues
"""
def post_setup(document_id):
    id = get_jwt_identity()
    name = request.json.get('name', None)
    if name == '':
        name = 'undefined'
    # NOTE check that doucment exists

    user = User.objects(id = id['$oid']).get()
    document = Document.objects(id = document_id).get()
    # save the setup to the DB
    setup = Setup(name = name, author = user, documentId = document, default = False).save()

    return Response(setup.to_json(), mimetype = 'application/json')

""" Renames A Setup
"""
def put_setup(document_id, setup_id):
    id = get_jwt_identity()
    name = request.json.get('name', None)
    default = request.json.get('default', None)
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(id = setup_id, author = user, documentId = document_id).get()
    setup.name = name if name else setup.name
    if default:
        Setup.objects(author = user, documentId = document_id, id__ne = setup_id).update(default = False)
        setup.default = default
    setup.save()
    return jsonify({'msg': 'Setup successfully updated', 'success': True})

""" Delete A Setup
"""
def delete_setup(document_id, setup_id):
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    # get setup
    setup = Setup.objects(id = setup_id, author = user, documentId = document_id).get()
    setup.delete()
    return jsonify({'msg': 'Setup successfully deleted', 'success': True})

""" Gets Setup Statistics
    NOTE: problems if state has not been loaded (this should be fixed when files are removed)
"""
def get_statistics(document_id, setup_id):
    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(author = user, id = setup_id, documentId = document_id).get()
    data = pd.read_json(setup.state, orient = 'split')
    statistics = []
    for column in data.columns:
        if column.startswith('.r_'):
            described = data[column].describe().to_json()
            described = json.loads(described)
            # the prefix of ._r always has length 3
            described.update(name = column[3:])
            statistics.append(described)

    response = jsonify(statistics)
    return response

""" Gets Setup Filter Options
    NOTE: when removing files get the dataframe from the Document state
"""
def get_filter_options(doucment_id):
    document = Document.objects(id = doucment_id).get()
    target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], document.path)
    data = pd.read_csv(target)

    map_types = data.dtypes
    options = []

    for column in data.columns:
        if column.startswith('.m_'):
            option = {
                "name": column[3:]
            }
            if map_types[column] == 'float64' or map_types[column] == 'int64':
                option.update(type = 'number')
            else:
                option.update(type = 'string')
                option.update(values = list(data[column].unique()))
            options.append(option)
        if column.startswith('.p'):
            option = {
                "name": column[2:],
                "type": "string",
                "values": list(data[column].unique())
            }
            options.append(option)

    return options