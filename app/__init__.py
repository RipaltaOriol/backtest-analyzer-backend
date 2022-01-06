import logging
from flask import Flask
from flask_cors import CORS
from mongoengine import *
from flask_jwt_extended import JWTManager
from mongoengine import document
from mongoengine.connection import connect

# Logger config
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Configuration
app.config.from_object('config.DevelopmentConfig')

# DB connection
connect(host = app.config['MONGO_URI'])

# JWT, CORS config
jwt = JWTManager(app)
CORS(app)

from app.controllers import UserController
from app.controllers import DocumentController
from app.controllers import LabController
from app.routes.document_bp import document_bp
from app.routes.lab_bp import lab_bp
from app.routes.auth_bp import auth_bp
from app.routes.error_bp import error_bp


# Blueprints
app.register_blueprint(document_bp, url_prefix='/documents')
app.register_blueprint(lab_bp, url_prefix='/labs')
app.register_blueprint(auth_bp)
app.register_blueprint(error_bp)

