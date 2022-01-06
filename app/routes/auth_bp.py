from flask import Blueprint
from app.controllers.UserController import login, signup

# Initialize blueprint
auth_bp = Blueprint('auth_bp', __name__)

auth_bp.route('/login', methods = ['POST'])(login)
auth_bp.route('/signup', methods = ['POST'])(signup)