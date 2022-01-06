import logging
from flask.blueprints import Blueprint
from app import app
from flask import Blueprint, jsonify, request

error_bp = Blueprint('error_bp', __name__)

@app.errorhandler(404)
def not_found(error=None):
  print(error)
  response = jsonify({
    'message': 'Resource Not Found: ' + request.url,
    'status': 404
  })
  response.status_code = 404
  return response