import json
import logging

from app.controllers.ErrorController import handle_401, handle_403
from app.models.Template import Template
from app.models.User import User
from app.models.UserSettings import UserSettings
from bson import json_util
from flask import jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from mongoengine.errors import NotUniqueError
from werkzeug.security import check_password_hash, generate_password_hash


def get_user_details():
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()

    user_settings = UserSettings.objects(user=user)

    if not user_settings:
        user_settings = UserSettings(user=user).save()
    else:
        user_settings = user_settings.get()

    templates = user_settings.get_templates()

    templates = {template.get("id"): template for template in templates}

    template_ids = [str(template.id) for template in user_settings.templates]

    market_templates = Template.objects().filter(id__not__in=template_ids).to_json()

    market_templates = json.loads(market_templates)

    for template in market_templates:
        template["id"] = template["_id"]["$oid"]
        template.pop("_id")

    market_templates = {template.get("id"): template for template in market_templates}

    return jsonify(
        {
            "email": user.email,
            "templates": templates,
            "marketTemplates": market_templates,
        }
    )


def post_user_template(templateId):
    """Add a Template to a User"""
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    template_to_add = Template.objects(id=templateId).get()

    user_settings = UserSettings.objects(user=user)
    if not user_settings:
        user_settings = UserSettings(user=user).save()

    user_settings.update(add_to_set__templates=template_to_add)

    return {"success": True, "msg": "Template added successfully."}


def login():
    """Login User"""
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    user = User.objects(email=email).first()
    if user == None:
        return handle_403(msg="Incorrect email or password")
    is_match = check_password_hash(user.password, password)
    if not is_match:
        return handle_403(msg="Incorrect email or password")

    user_id = json.loads(json_util.dumps(user.id))
    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)
    response = jsonify(
        {
            "user": user_id["$oid"],
            "msg": "Login successful",
            "access_token": access_token,
            "success": True,
        }
    )
    set_refresh_cookies(response, refresh_token)
    return response


def signup():
    """Signup User"""
    # Receiving data
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    default_template = Template.objects(name="Default").get()
    if email and password:
        hashed_password = generate_password_hash(password)
        user = User(email=email, password=hashed_password)

        # return "Hello"
        try:
            user = user.save()
            # setup user settings
            UserSettings(user=user, templates=[default_template]).save()

            user_id = json.loads(json_util.dumps(user.id))
            access_token = create_access_token(identity=user_id)
            refresh_token = create_refresh_token(identity=user_id)
            response = jsonify(
                {
                    "user": user_id["$oid"],
                    "msg": "Login successful",
                    "access_token": access_token,
                    "success": True,
                }
            )
            set_refresh_cookies(response, refresh_token)
            return response
        except NotUniqueError as error:
            print(error)
            return handle_403(msg="Something went wrong")
    else:
        return handle_401(msg="Missing email or password")


def update_password():
    """Update password"""
    id = get_jwt_identity()
    password = request.json.get("password", None)
    hashed_password = generate_password_hash(password)

    User.objects(id=id["$oid"]).update(password=hashed_password)
    return {"success": True, "msg": "Password updated successfully."}


def logout():
    """Logouut User"""
    response = jsonify({"msg": "Logout successful"})
    unset_jwt_cookies(response)
    return response


def refresh():
    """Refresh Token"""
    id = get_jwt_identity()
    access_token = create_access_token(identity=id)
    response = jsonify(
        {"access_token": access_token, "user": id["$oid"], "success": True}
    )
    return response


def authorized():
    """Route: Check if Authorized"""
    return jsonify({"status": "OK"})
