from flask import jsonify

def handle_401():
  return jsonify({'msg': 'Incorrect email or password'}), 401