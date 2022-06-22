import json

from os import abort
from bson import json_util
from flask import request, jsonify
from mongoengine.errors import NotUniqueError
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended import set_refresh_cookies, unset_jwt_cookies
from flask_jwt_extended import get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from app.models.User import User
from app.controllers.ErrorController import handle_401, handle_403

""" Login User
"""
def login():
  email = request.json.get('email', None)
  password = request.json.get('password', None)
  user = User.objects(email = email).first()
  print('Here:')
  if user == None:
    return handle_403(msg = 'Incorrect email or password')
  # FIX: if nothing is found then respond something
  is_match = check_password_hash(user.password, password)
  if not is_match:
      return handle_403(msg = 'Incorrect email or password')

  user_id = json.loads(json_util.dumps(user.id))
  access_token = create_access_token(identity = user_id)
  refresh_token = create_refresh_token(identity = user_id)
  response = jsonify({
    'user': user_id['$oid'],
    'msg': 'Login successful',
    'access_token': access_token,
    'success': True
  })
  set_refresh_cookies(response, refresh_token)
  return response

""" Signup User
    NOTE: currently not working
"""
def signup():
  # Receiving data
  email = request.json['email']
  password = request.json['password']
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

""" Logouut User
"""
def logout():
  print('Hitting this')
  response = jsonify({"msg": "Logout successful"})
  unset_jwt_cookies(response)
  return response

""" Refresh Token
"""
def refresh():
  id = get_jwt_identity()
  access_token = create_access_token(identity = id)
  response = jsonify({
    'access_token': access_token,
    'success': True
  })
  return response

""" Test Route: Check if Authorized
"""
def authorized():
  return jsonify({'status': 'OK'})