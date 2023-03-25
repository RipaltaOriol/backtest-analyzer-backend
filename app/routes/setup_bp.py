from app.controllers.PDFController import get_file
from app.controllers.SetupController import (
    delete_setup,
    get_graphics,
    get_graphs,
    get_setup,
    get_setups,
    get_statistics,
    post_setup,
    put_setup,
    put_setup_row,
)
from flask import Blueprint
from flask_jwt_extended import jwt_required

# Initialize blueprint
setup_bp = Blueprint("setup_bp", __name__)

setup_bp.route("", methods=["GET"])(jwt_required()(get_setups))
setup_bp.route("", methods=["POST"])(jwt_required()(post_setup))
# setup_bp.route('/<setup_id>', methods = ['GET'])(jwt_required()(get_setup))
setup_bp.route("/<setup_id>", methods=["PUT"])(jwt_required()(put_setup))
setup_bp.route("/<setup_id>", methods=["DELETE"])(jwt_required()(delete_setup))
setup_bp.route("/<setup_id>/file", methods=["GET"])(jwt_required()(get_file))
setup_bp.route("/<setup_id>/stats", methods=["GET"])(jwt_required()(get_statistics))
setup_bp.route("/<setup_id>/charts", methods=["GET"])(jwt_required()(get_graphics))
# eventually move the graphs call to this method
setup_bp.route("/<setup_id>/graphs", methods=["GET"])(jwt_required()(get_graphs))

# API calls for setup rows
setup_bp.route("/<setup_id>/<row_id>/note", methods=["POST"])(
    jwt_required()(put_setup_row)
)
