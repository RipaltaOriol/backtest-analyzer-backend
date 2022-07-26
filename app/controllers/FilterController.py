import os
import json
import numpy as np
from app import app
import pandas as pd
from io import StringIO
from flask import request, jsonify
from flask.wrappers import Response

from app.models.Setup import Setup
from app.models.Filter import Filter
from app.models.Document import Document
from app.controllers.ErrorController import handle_403
from app.controllers.SetupController import get_filter_options



# Encoder to deal with numpy Boolean values
class CustomJSONizer(json.JSONEncoder):
    def default(self, obj):
        return super().encode(bool(obj)) \
            if isinstance(obj, np.bool_) \
            else super().default(obj)

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

""" Generates filter name
"""
def get_filter_name(column, operation, value):
  # initialise the name variable
  name = ''
  # get the column
  if column.startswith('.p'):
    name += 'Pair'
  else:
    name += column[3:]
  if operation == 'gt':
    name += ' greater than '
  elif operation == 'lt':
    name += ' lesser than '
  elif operation == 'eq':
    name += ' equal to '
  elif operation == 'ne':
    name += ' not equal to '
  elif operation == 'in':
    name += ' includes '
  elif operation == 'nin':
    name += ' not includs '
  # attach values
  values = ', '.join(str(v) for v in value)
  name += values
  return name

""" Adds a Filter to a Setup
"""
def post_filter(setup_id):
  column = request.json.get('column', None)
  operation = request.json.get('operation', None)
  value = request.json.get('value', None)
  setup = Setup.objects(id = setup_id).get()
  temp = json.dumps(setup.state)
  data = pd.read_json(StringIO(temp), orient='table')

  if column == None or operation == None or value == None:
    return handle_403(msg = 'Filter is not valid')

  data = apply_filter(data, column, operation, value)
  name = get_filter_name(column, operation, value)
  df = data.to_json(orient = 'table')
  df = json.loads(df)
  filter = Filter(
    name = name,
    column = column,
    operation = operation,
    value = value,
  ).save()

  setup.filters.append(filter)
  setup.save()
  setup.modify(state = df)
  response = setup.to_json()
  response = json.loads(response)
  # loads options and appends them to setup
  options = get_filter_options(setup.documentId.id)
  response.update(options = options)
  response = json.dumps(response, cls = CustomJSONizer)

  return Response(response, mimetype = 'application/json')

""" Adds a Filter to a Setup
"""
def delete_filter(setup_id, filter_id):
  try:
    setup = Setup.objects(id = setup_id).get()  
    filter_dlt = Filter.objects(id = filter_id).get()
    # delete filter instance in setup
    to_dlt = filter_dlt.pk
    setup.modify(pull__filters = to_dlt)

    # establish remaining filters
    document = Document.objects(id = setup.documentId.id).get()
    temp = json.dumps(document.state)
    df = pd.read_json(StringIO(temp), orient = 'table')

    for filter in setup.filters:
      df = apply_filter(df, filter.column, filter.operation, filter.value)

    df = df.to_json(orient = 'table')
    df = json.loads(df)
    setup.modify(state = df)

    # delete filter
    filter_dlt.delete()

    response = setup.to_json()
    response = json.loads(response)
    # loads options and appends them to setup
    options = get_filter_options(setup.documentId.id)
    response.update(options = options)
    response = json.dumps(response, cls = CustomJSONizer)

    return Response(response, mimetype = 'application/json')
    
  except:
    return handle_403(msg = 'Somethign went wrong')
  