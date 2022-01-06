from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.controllers.DocumentController import get_document, get_documents
from app.controllers.DocumentController import post_document

# Initialize blueprint
document_bp = Blueprint('document_bp', __name__)

document_bp.route('', methods = ['GET'])(jwt_required()(get_documents))
document_bp.route('/<id>', methods = ['GET'])(jwt_required()(get_document))
document_bp.route('/upload', methods = ['POST'])(jwt_required()(post_document))
