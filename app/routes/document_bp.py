from app.controllers.DocumentController import (
    clone_document,
    create_document,
    delete_document,
    get_calendar_table,
    get_document,
    get_document_columns,
    get_document_compare,
    get_documents,
    post_document,
    put_document,
    update_document,
    fetch_metatrader,
    refetch_document,
)

from app.controllers.TemplateController import (
    assing_template_to_document,
    get_template_mapping,
)

from flask import Blueprint
from flask_jwt_extended import jwt_required

# Initialize blueprint
document_bp = Blueprint("document_bp", __name__)

document_bp.route("", methods=["GET"])(jwt_required()(get_documents))
document_bp.route("", methods=["POST"])(jwt_required()(create_document))

document_bp.route("/upload", methods=["POST"])(jwt_required()(post_document))
document_bp.route("/fetch", methods=["POST"])(jwt_required()(fetch_metatrader))
document_bp.route("/<file_id>", methods=["GET"])(jwt_required()(get_document))
document_bp.route("/<file_id>", methods=["POST"])(jwt_required()(clone_document))
document_bp.route("/<file_id>", methods=["PUT"])(jwt_required()(put_document))
document_bp.route("/<file_id>", methods=["DELETE"])(jwt_required()(delete_document))

document_bp.route("/<file_id>/columns", methods=["GET"])(
    jwt_required()(get_document_columns)
)
document_bp.route("/<file_id>/compare", methods=["GET"])(
    jwt_required()(get_document_compare)
)
document_bp.route("/<file_id>/update", methods=["PUT"])(jwt_required()(update_document))
document_bp.route("/<file_id>/refetch", methods=["PUT"])(
    jwt_required()(refetch_document)
)

document_bp.route("/<document_id>/calendar", methods=["GET"])(
    jwt_required()(get_calendar_table)
)

document_bp.route("/<document_id>/templates/<template_id>", methods=["POST"])(
    jwt_required()(assing_template_to_document)
)
document_bp.route("/<document_id>/templates/mapping", methods=["GET"])(
    jwt_required()(get_template_mapping)
)
