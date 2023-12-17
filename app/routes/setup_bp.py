from app.controllers.PDFController import get_file
from app.controllers.SetupController import (
    delete_setup,
    get_bubble_results,
    get_calendar_table,
    get_cumulative_results,
    get_daily_distribution,
    get_graphics,
    get_graphs,
    get_net_results,
    get_setup,
    get_setup_row,
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
setup_bp.route("/<document_id>/<row_id>", methods=["GET"])(
    jwt_required()(get_setup_row)
)
setup_bp.route("/<setup_id>/<row_id>", methods=["POST"])(jwt_required()(put_setup_row))

setup_bp.route("<setup_id>/charts/bubble", methods=["GET"])(
    jwt_required()(get_bubble_results)
)

setup_bp.route("/<setup_id>/stats/daily", methods=["GET"])(
    jwt_required()(get_daily_distribution)
)

setup_bp.route("/<setup_id>/charts/net", methods=["GET"])(
    jwt_required()(get_net_results)
)
setup_bp.route("/<setup_id>/charts/cum", methods=["GET"])(
    jwt_required()(get_cumulative_results)
)

setup_bp.route("/<setup_id>/calendar", methods=["GET"])(
    jwt_required()(get_calendar_table)
)
