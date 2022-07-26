import os
import json
import shutil
import pandas as pd

from app import app
from flask import request, jsonify
from werkzeug.utils import secure_filename
from flask_jwt_extended import get_jwt_identity

from app.models.User import User
from app.models.Setup import Setup
from app.models.Document import Document

""" Retrieves All Documents
"""
def get_documents():
  documents = []
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  files = Document.objects(author = user)
  for file in files:
    document = {
      'id': str(file.id),
      'name': file.name,
      'date': file.date_created
    }
    documents.append(document)
  response = jsonify(documents)
  return response

""" Update Doucment
"""
def put_document(file_id):
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  # get the document and its new name
  name = request.json.get('name', None)
  name = secure_filename(name)
  file = Document.objects(id = file_id, author = user).get()
  file.name = name
  file.save()
  return jsonify({'msg': 'Document successfully updated', 'success': True})

""" Upload Document
"""
def post_document():
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  # get file
  file = request.files['file']
  # check that it is a CSV file
  if file.content_type == 'text/csv':
    # transform Dataframe
    df = pd.read_csv(file)
    # include in how-to
    # drop emtpy rows / columns
    # df.dropna(axis = 1, inplace=True)
    df = df.to_json(orient = 'table')
    df = json.loads(df)

    filename = secure_filename(file.filename)
    # check if file exists
    is_file_exists = Document.objects(name = filename, author = user)
    if len(is_file_exists) > 0:
      return jsonify({'msg': 'This file already exists', 'success': False})

    # save the file to the DB  
    document = Document(
      name = filename,
      author = user,
      state = df
    )
    document.save()
    # save the default setup to the DB
    setup = Setup(
      name = 'Default',
      author = user,
      documentId = document,
      default = True,
      state = df
    )
    setup.save()

    return jsonify({'msg': 'Document successfully uploaded', 'success': True})
  else:
    return jsonify({'msg': 'File is not an accepted format', 'success': False})

""" Duplicates Existing File
    NOTE: It could be abstracted
"""
def clone_document(file_id):
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  # get the document and initialise a counter
  copy_counter = 1
  file = Document.objects(id = file_id).get()
  # get the path and the new name
  original = file.name
  new_name = secure_filename(original + ' Copy' + str(copy_counter))

  is_file_exists = Document.objects(name = new_name)
  while len(is_file_exists) > 0:
      copy_counter += 1
      new_name = secure_filename(original + ' Copy' + str(copy_counter))
      is_file_exists = Document.objects(name = new_name)
    
  # save the copy to the DB  
  document = Document(
    name = new_name,
    author = user,
    state = file.state
  )
  document.save()
  # save the default setup to the DB
  setup = Setup(
    name = 'Default',
    author = user,
    documentId = document,
    default = True,
    state = file.state
  )
  setup.save()
  return jsonify({'msg': 'Document successfully copied', 'success': True})


""" Delete Document
NOTE: make suer document belongs to the author
"""
def delete_document(file_id):
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  # get the document
  file = Document.objects(id = file_id, author = user).get()
  try:
    # delete setups
    Setup.objects(documentId = file.id).delete()
    # delete file in DB
    file.delete()
    return jsonify({'msg': 'Document successfully deleted', 'success': True})
  except:
    return jsonify({'msg': 'Document does not exist', 'success': False})