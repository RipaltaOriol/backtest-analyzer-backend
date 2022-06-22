from flask import jsonify

""" 401 Error
"""
def handle_401(msg):
  return jsonify({'msg': msg}), 401

""" 403 Error
"""
def handle_403(msg):
  return jsonify({
    'msg': msg,
    'success': False
  }), 403