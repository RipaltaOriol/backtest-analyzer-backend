import os
import logging
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from mongoengine import *
from flask_jwt_extended import JWTManager
from mongoengine import document
from mongoengine import connect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger config
logging.basicConfig(level=logging.DEBUG)
# logging.getLogger('flask_cors').level = logging.DEBUG

app = Flask(__name__)

# JWT, CORS config
jwt = JWTManager(app)
CORS(app, supports_credentials = True)

# Configuration
app.secret_key = 'secret-backtest-analyzer'
# app.config.from_object('')
app.config.from_object(os.getenv("APP_ENV"))

app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_COOKIE_SAMESITE"] = 'None'
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
# The default settings are fine
# app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds = 5)
# app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(minutes = 1)

# DB connection
connect(host = app.config['MONGO_URI'])

# from app.controllers import UserController
# from app.controllers import DocumentController
# from app.controllers import FilterController
# from app.controllers import SetupController
# from app.controllers import PDFController
# from app.controllers import ErrorController
from app.routes.document_bp import document_bp
from app.routes.setup_bp import setup_bp
from app.routes.filter_bp import filter_bp
from app.routes.auth_bp import auth_bp
from app.routes.error_bp import error_bp

# JWT Custom Behaviour
@jwt.expired_token_loader
def my_expired_token_callback(jwt_header, jwt_payload):
    return jsonify(err = "Token has expired"), 403

# Blueprints
app.register_blueprint(document_bp, url_prefix='/documents')
app.register_blueprint(setup_bp, url_prefix='/setups')
app.register_blueprint(filter_bp, url_prefix='/setups/<setup_id>/filters')
app.register_blueprint(auth_bp)
app.register_blueprint(error_bp)

