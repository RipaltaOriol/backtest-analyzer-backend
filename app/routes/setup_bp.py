from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers.SetupController import get_setups, get_setup
from app.controllers.SetupController import post_setup
from app.controllers.SetupController import put_setup
from app.controllers.SetupController import delete_setup

# Initialize blueprint
setup_bp = Blueprint('setup_bp', __name__)

setup_bp.route('', methods = ['GET'])(jwt_required()(get_setups))
setup_bp.route('', methods = ['POST'])(jwt_required()(post_setup))
setup_bp.route('/<setup_id>', methods = ['GET'])(jwt_required()(get_setup))
setup_bp.route('/<setup_id>', methods = ['PUT'])(jwt_required()(put_setup))
setup_bp.route('/<setup_id>', methods = ['DELETE'])(jwt_required()(delete_setup))