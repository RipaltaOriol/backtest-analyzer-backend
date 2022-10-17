from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers.DocumentController import get_documents, get_documents_setups, get_document_compare
from app.controllers.DocumentController import post_document, clone_document
from app.controllers.DocumentController import put_document
from app.controllers.DocumentController import delete_document

# Initialize blueprint
document_bp = Blueprint('document_bp', __name__)

document_bp.route('', methods = ['GET'])(jwt_required()(get_documents))
document_bp.route('/extended', methods = ['GET'])(jwt_required()(get_documents_setups))
document_bp.route('/upload', methods = ['POST'])(jwt_required()(post_document))
document_bp.route('/<file_id>', methods = ['POST'])(jwt_required()(clone_document))
document_bp.route('/<file_id>', methods = ['PUT'])(jwt_required()(put_document))
document_bp.route('/<file_id>', methods = ['DELETE'])(jwt_required()(delete_document))

document_bp.route('/<file_id>/compare', methods = ['GET'])(jwt_required()(get_document_compare))

