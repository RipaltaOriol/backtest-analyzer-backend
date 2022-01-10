from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers.LabController import get_labs, get_lab
from app.controllers.LabController import create_lab, get_filter, put_filter, patch_note

# Initialize blueprint
lab_bp = Blueprint('lab_bp', __name__)

lab_bp.route('', methods = ['GET'])(jwt_required()(get_labs))
lab_bp.route('', methods = ['POST'])(jwt_required()(create_lab))
lab_bp.route('/<id>', methods = ['GET'])(jwt_required()(get_lab))
lab_bp.route('/<id>/filter', methods = ['GET'])(jwt_required()(get_filter))
lab_bp.route('/<id>/filter', methods = ['PUT'])(jwt_required()(put_filter))
lab_bp.route('/<id>/note', methods = ['PATCH'])(jwt_required()(patch_note))
