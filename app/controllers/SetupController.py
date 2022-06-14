import os
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
        df = df.to_json(orient='split')
        setup.modify(state = df)
    return Response(setup.to_json(), mimetype='application/json')

""" Creates A New Setup
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

    return Response(setup.to_json(), mimetype='application/json')

""" Renames A Setup
"""
def put_setup(document_id, setup_id):
    id = get_jwt_identity()
    name = request.json.get('name', None)
    user = User.objects(id = id['$oid']).get()
    setup = Setup.objects(id = setup_id, author = user, documentId = document_id).get()
    setup.name = name
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