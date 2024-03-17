from app.controllers.TradeController import delete_trade, post_trade, put_trade
from flask import Blueprint
from flask_jwt_extended import jwt_required

# Initialize blueprint
trade_bp = Blueprint("trade_bp", __name__)


trade_bp.route("", methods=["POST"])(jwt_required()(post_trade))

trade_bp.route("/<trade_id>", methods=["DELETE"])(jwt_required()(delete_trade))

trade_bp.route("/<trade_id>", methods=["PUT"])(jwt_required()(put_trade))
