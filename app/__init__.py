import logging
import os
from datetime import timedelta

import sentry_sdk
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from mongoengine import *
from mongoengine import connect, document
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration

# Load environment variables
load_dotenv()

# Logger config
logging.basicConfig(
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level=logging.INFO,
)
# logging.getLogger("flask_cors").level = logging.DEBUG

if os.getenv("SENTRY_ENVIRONMENT") == "production":
    # sentry monitor
    sentry_sdk.init(
        dsn="https://4846760153f545fd828547b8e389686f@o4505359772811264.ingest.sentry.io/4505359774515200",
        enable_tracing=True,
        integrations=[
            FlaskIntegration(
                transaction_style="url",
            ),
            HttpxIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        request_bodies="always",
        environment=os.getenv("SENTRY_ENVIRONMENT"),
    )

app = Flask(__name__)

# JWT, CORS config
jwt = JWTManager(app)

CORS(app, supports_credentials=True)

# Configuration
app.secret_key = "secret-backtest-analyzer"

app.json.sort_keys = False

app.config.from_object(os.getenv("APP_ENV"))
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_COOKIE_SAMESITE"] = "None"
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

# DB connection
connect(host=os.getenv("MONGO_URI"))

from app.routes.auth_bp import auth_bp
from app.routes.document_bp import document_bp
from app.routes.error_bp import error_bp
from app.routes.filter_bp import filter_bp
from app.routes.setup_bp import setup_bp
from app.routes.trade_bp import trade_bp
from app.routes.user_bp import user_bp


# JWT Custom Behaviour
@jwt.expired_token_loader
def my_expired_token_callback(jwt_header, jwt_payload):
    return jsonify(err="Token has expired"), 403


# Blueprints
app.register_blueprint(document_bp, url_prefix="/documents")
app.register_blueprint(trade_bp, url_prefix="/documents/<account_id>/trade")
app.register_blueprint(user_bp, url_prefix="/users")
app.register_blueprint(setup_bp, url_prefix="/setups")
app.register_blueprint(filter_bp, url_prefix="/setups/<setup_id>/filters")
app.register_blueprint(auth_bp)
app.register_blueprint(error_bp)
