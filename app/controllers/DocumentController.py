import os
import shutil

from app import app
from flask import request, jsonify
from werkzeug.utils import secure_filename
from flask_jwt_extended import get_jwt_identity

from app.models.User import User
from app.models.Setup import Setup
from app.models.Document import Document
from app.controllers.FileController import get_statistics, prettify_table

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
      'name': file.title,
      'date': file.date_created
    }
    documents.append(document)
  response = jsonify(documents)
  return response

""" Clone Doucment
"""
def put_document(file_id):
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  # get the document and its new name
  name = request.json.get('name', None)
  name = secure_filename(name)
  file = Document.objects(id = file_id).get()
  # get the old path
  old_path = file.path
  # update file in directory
  target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], old_path)
  new = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], str(user.id), name)
  # check if file name already exists
  if not os.path.exists(new):
    os.rename(target, new)
    # update file
    file.path = str(user.id) + '/' + name
    file.title = name
    file.save()
    return jsonify({'msg': 'Document successfully updated', 'success': True})
  else:
    return jsonify({'msg': 'File with this name already exist', 'success': False})

""" Upload Document
"""
def post_document():
  id = get_jwt_identity()
  user = User.objects(id = id['$oid']).get()
  # get target directory
  target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], str(user.id))
  print(target)
  # create one if it does not exist
  if not os.path.isdir(target):
    os.mkdir(target)

  # get file
  file = request.files['file']
  # check that it is a CSV file
  if file.content_type == 'text/csv':
    filename = secure_filename(file.filename)
    # check if file exists
    is_file_exists = Document.objects(title = filename)
    if len(is_file_exists) > 0:
      return jsonify({'msg': 'This file already exists', 'success': False})

    destination="/".join([target, filename])
    file.save(destination)

    # I do not know why this line was here
    # session['uploadFilePath'] = destination

    # save the file to the DB  
    document = Document(
      title = filename,
      path = str(user.id) + '/' + filename,
      author = user
    )
    document.save()
    # save the default setup to the DB
    setup = Setup(
      name = 'Default',
      author = user,
      documentId = document,
      default = True
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
  path = file.path
  name = file.title
  title = secure_filename(name + ' Copy' + str(copy_counter))
  # update file in directory
  target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], path)
  new = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], str(user.id), title)
  # if file already exists then update the title
  while os.path.exists(new):
    copy_counter += 1
    title = secure_filename(name + ' Copy' + str(copy_counter))
    new = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], str(user.id), title)

  shutil.copyfile(target, new)
  # save the copy to the DB  
  document = Document(
    title = title,
    path = str(user.id) + '/' + title,
    author = user
  )
  document.save()
  # save the default setup to the DB
  setup = Setup(
    name = 'Default',
    author = user,
    documentId = document,
    default = True
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
  file = Document.objects(id = file_id).get()
  # get the path
  path = file.path
  # delete file in directory
  target = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], path)
  if os.path.exists(target):
    os.remove(target)
    # delete setups
    Setup.objects(documentId = file.id).delete()
    # delete file in DB
    file.delete()
    return jsonify({'msg': 'Document successfully deleted', 'success': True})
  else:
    return jsonify({'msg': 'Document does not exist', 'success': False})