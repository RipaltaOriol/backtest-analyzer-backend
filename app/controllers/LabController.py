from app import app
import os
import pandas as pd
from bson import json_util
from flask import jsonify, request
from flask.wrappers import Response
from werkzeug.wrappers import response
from flask_jwt_extended import get_jwt_identity

from app.models.Document import Document
from app.models.Lab import Lab
from app.models.User import User
from app.controllers.FilterController import apply_filter
from app.controllers.FileController import get_statistics, prettify_table, get_columns

def create_lab():
  id = get_jwt_identity()
  name = request.json.get('name', None)
  if name == '':
    name = 'undefined'
  file_id = request.json.get('file', None)
  user = User.objects(id = id['$oid']).get()
  file = Document.objects(id = file_id).get()
  path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], file.title)
  df = pd.read_csv(path)
  df = df.to_json(orient='split')
  lab = Lab(name = name, author = user,  documentId = file, state = df).save()
  return Response(lab.to_json(), mimetype='application/json')

def get_lab(id):
  lab = Lab.objects(id = id).first()
  state = lab.state

  if not bool(state):
    # if state does not exists then save it
    file = Document.objects(id = lab.documentId.id).get()
    path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], file.title)
    df = pd.read_csv(path)
    df = df.to_json(orient='split')
    lab.modify(state = df)
    state = lab.state
  
  df = pd.read_json(state, orient='split')
  df_stats = get_statistics(df)
  df = prettify_table(df)
  df_json = df.to_json(orient='records')
  df_stats_json = df_stats.to_json(orient='split')
  response = jsonify({
    'table': df_json,
    'stats': df_stats_json,
    'filters': lab.filters,
    'columns': list(df.columns),
    'notes': lab.notes
  })
  return response

def get_labs():
  id = get_jwt_identity()
  labs = []
  user = User.objects(id = id['$oid']).get()
  files = Lab.objects(author = user)
  for file in files:
    lab = {
      'id': str(file.id),
      'name': file.name
    }
    labs.append(lab)
  response = jsonify({'labs': labs})
  return response

def get_filter(id):
  print(id)
  print(type(id))
  lab = Lab.objects(id = id).first()
  df = pd.read_json(lab.state, orient='split')
  columns = get_columns(df)
  return columns

def put_filter(id):  
  # FIX: add authorization
  lab = Lab.objects(id = id).first()
  df = pd.read_json(lab.state, orient='split')
  method = request.args.get('method')
  filter = request.json.get('filter', None)
  action = request.json.get('action', None)
  value = request.json.get('value', None)

  put_filter = {
    'filter': filter,
    'action': action,
    'value': value
    }
  
  if method == 'add':
    df = apply_filter(df, filter, action, value)
    lab.filters.append(put_filter)

  elif method == 'delete':
    lab.filters.remove(put_filter)
    file = Document.objects(id = lab.documentId.id).get()
    path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], file.title)
    df = pd.read_csv(path)
    for filter in lab.filters:
      df = apply_filter(df, filter['filter'], filter['action'], filter['value'])

  else:
    return 'Throw and error here'

  new_state = df.to_json(orient='split')
  lab.update(filters = lab.filters, state = new_state)
  df_stats = get_statistics(df)
  df = prettify_table(df)
  df_json = df.to_json(orient='records')
  df_stats_json = df_stats.to_json(orient='split')
  response = jsonify({
    'table': df_json,
    'stats': df_stats_json,
    'filters': lab.filters,
    'columns': list(df.columns)
  })
  return response

def patch_note(id):
  note = request.json.get('note', '')
  lab = Lab.objects(id = id).first()
  lab.modify(notes = note)
  return lab.notes
