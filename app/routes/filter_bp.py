from app.controllers.FilterController import delete_filter, post_filter
from flask import Blueprint
from flask_jwt_extended import jwt_required

# Initialize blueprint
filter_bp = Blueprint("filter_bp", __name__)

filter_bp.route("", methods=["POST"])(jwt_required()(post_filter))
filter_bp.route("/<filter_id>", methods=["DELETE"])(jwt_required()(delete_filter))
