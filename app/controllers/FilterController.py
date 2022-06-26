import os
from app import app
import pandas as pd
from flask import request, jsonify
from flask.wrappers import Response
from flask_jwt_extended import get_jwt_identity

from app.models.Setup import Setup
from app.models.Filter import Filter
from app.models.Document import Document
from app.controllers.ErrorController import handle_403

""" Applies a Filter to a dataframe
"""
def apply_filter(df, column, operation, value):
  if operation == 'in' or operation == 'nin':
    if operation == 'in':
      df = df[df[column].isin(value)]
    elif operation == 'nin':
      df = df[-df[column].isin(value)]
  else:
    # update the value so that it only gets the first element
    value = value[0]
    if operation == 'gt':
      df = df[df[column] > value]
    elif operation == 'lt':
      df = df[df[column] < value]
    elif operation == 'eq':
      df = df[df[column] == value]
    elif operation == 'ne':
      df = df[df[column] != value]
  
  return df

""" Adds a Filter to a Setup
"""
def post_filter(setup_id):
  id = get_jwt_identity()
  column = request.json.get('column', None)
  operation = request.json.get('operation', None)
  value = request.json.get('value', None)
  setup = Setup.objects(id = setup_id).get()
  data = pd.read_json(setup.state, orient='split')

  if column == None or operation == None or value == None:
    return handle_403(msg = 'Filter is not valid')

  data = apply_filter(data, column, operation, value)
    
  state = data.to_json(orient='split')

  filter = Filter(
    column = column,
    operation = operation,
    value = value,
  ).save()

  setup.filters.append(filter)
  setup.state = state
  setup.save()

  return Response(setup.to_json(), mimetype = 'application/json')

""" Adds a Filter to a Setup
"""
def delete_filter(setup_id, filter_id):
  try:
    setup = Setup.objects(id = setup_id).get()  
    filter_dlt = Filter.objects(id = filter_id).get()
    to_dlt = filter_dlt.pk
    
    setup.update(pull__filters = to_dlt)
    
    # establish remaining filters
    document = Document.objects(id = setup.documentId.id).get()
    target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], document.path)
    df = pd.read_csv(target)

    for filter in setup.filters:
      df = apply_filter(df, filter.column, filter.operation, filter.value)

    df = df.to_json(orient = 'split')
    setup.update(state = df)
    # delete filter
    filter_dlt.delete()
    return jsonify({'msg': 'Filter successfully deleted', 'success': True})
    
  except:
    return handle_403(msg = 'Somethign went wrong')
  