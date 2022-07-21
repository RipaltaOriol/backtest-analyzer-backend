from flask import Blueprint
from flask_cors import CORS, cross_origin
from flask_jwt_extended import jwt_required
from app.controllers.UserController import login, signup, logout, refresh, authorized

# Initialize blueprint
auth_bp = Blueprint('auth_bp', __name__)

auth_bp.route('/login', methods = ['POST'])(login)
auth_bp.route('/signup', methods = ['POST'])(signup)
auth_bp.route('/refresh', methods = ['GET'])(cross_origin(allow_headers=['Content-Type','Authorization'])(jwt_required(refresh=True)(refresh)))
auth_bp.route('/logout', methods=['POST'])(jwt_required(refresh=True)(logout))

# Test Route
auth_bp.route('/authorized', methods = ['GET'])(jwt_required()(authorized))
