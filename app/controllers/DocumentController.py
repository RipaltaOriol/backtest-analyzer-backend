from logging import currentframe, error
import os
import pandas as pd
from app import app
from flask import request, session, jsonify
from werkzeug.utils import secure_filename
from flask_jwt_extended import get_jwt_identity
from app.models.User import User
from app.models.Document import Document
from app.controllers.FileController import get_columns, get_statistics, prettify_table


def get_documents():
  documents = []
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  files = Document.objects(author = user)
  for file in files:
    document = {
      'id': str(file.id),
      'name': file.title
    }
    documents.append(document)
  response = jsonify({'documents': documents})
  return response

def get_document(id):
  # FIX: add authorization to check the file corresponds to the user
  file = Document.objects(id = id).get()

  path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], file.title)
  df = pd.read_csv(path)
  df_stats = get_statistics(df)
  df = prettify_table(df)
  df_json = df.to_json(orient='split')
  df_stats_json = df_stats.to_json(orient='split')
  response = jsonify({
    'table': df_json,
    'stats': df_stats_json
  })
  return response


def post_document():
  id = get_jwt_identity()
  target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])

  if not os.path.isdir(target):
    os.mkdir(target)
  file = request.files['file']

  if '.' in file.filename and file.filename.rsplit('.', 1)[1] in 'csv':
    
    filename = secure_filename(file.filename)
    file_exists = Document.objects(title = filename)
    if len(file_exists) > 0:
      return jsonify({'msg': 'This file already exists', 'success': False})

    destination="/".join([target, filename])
    file.save(destination)
    session['uploadFilePath'] = destination

    id = get_jwt_identity()
    user = User.objects(id = id['$oid']).get()
    lab_file = Document(
      title = filename,
      identifier = str(user.id) + '/' + filename,
      path = filename,
      author = user
    )
    lab_file.save()
    return jsonify({'msg': 'Document successfully uploaded', 'success': True})
  else:
    return jsonify({'msg': 'File is not an accepted format', 'success': False})

