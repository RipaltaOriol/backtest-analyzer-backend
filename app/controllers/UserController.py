from os import abort
import json
from flask import Response, request, jsonify
from flask_jwt_extended import create_access_token
from mongoengine.errors import NotUniqueError
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util
from bson.objectid import ObjectId
from app.models.User import User

def login():
  email = request.json.get('email', None)
  password = request.json.get('password', None)
  user = User.objects(email = email)[0]
  # FIX: if nothing is found then respond something
  is_match = check_password_hash(user.password, password)
  if not is_match:
      return jsonify({'msg': 'Bad username or password'}), 401

  token_id = json.loads(json_util.dumps(user.id))
  access_token = create_access_token(identity = token_id)
  return jsonify(access_token=access_token)

def signup():
  # Receiving data
  email = request.json['email']
  password = request.json['password']
  print('Request received')
  if email and password:
    hashed_password = generate_password_hash(password)
    user = User(
      email = email,
      password = hashed_password
    )
    try:
      user = user.save()
      token_id = json.loads(json_util.dumps(user.id))
      access_token = create_access_token(identity = token_id)
      return jsonify(access_token=access_token)
    except NotUniqueError:
      abort(404)

