from app.controllers.UserController import get_user_details, post_user_template
from flask import Blueprint
from flask_jwt_extended import jwt_required

# Initialize blueprint
user_bp = Blueprint("user_bp", __name__)

# TODO: change the naming of this endpoint - its not intuitive
user_bp.route("/details", methods=["GET"])(jwt_required()(get_user_details))

user_bp.route("/templates/<templateId>", methods=["POST"])(
    jwt_required()(post_user_template)
)
