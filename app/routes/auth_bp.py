from app.controllers.UserController import (
    authorized,
    login,
    logout,
    refresh,
    signup,
    update_password,
)
from flask import Blueprint
from flask_cors import CORS, cross_origin
from flask_jwt_extended import jwt_required

# Initialize blueprint
auth_bp = Blueprint("auth_bp", __name__)

auth_bp.route("/login", methods=["POST, OPTIONS"])(login)
auth_bp.route("/signup", methods=["POST"])(signup)
auth_bp.route("/logout", methods=["POST"])(jwt_required()(logout))
auth_bp.route("/update-password", methods=["PUT"])(jwt_required()(update_password))
auth_bp.route("/refresh", methods=["GET"])(jwt_required(refresh=True)(refresh))

# Test Route
auth_bp.route("/authorized", methods=["GET"])(jwt_required()(authorized))
