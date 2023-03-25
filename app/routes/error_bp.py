import logging

from app import app
from flask import Blueprint, jsonify, request
from flask.blueprints import Blueprint

error_bp = Blueprint("error_bp", __name__)


@app.errorhandler(404)
def not_found(error=None):
    response = jsonify({"message": "Resource Not Found: " + request.url, "status": 404})
    response.status_code = 404
    return response
