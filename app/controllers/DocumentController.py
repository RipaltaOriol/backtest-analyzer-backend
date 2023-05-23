import json
import os
import re
import shutil
import uuid
from io import StringIO

import pandas as pd
from app import app
from app.controllers.errors import UploadError
from app.controllers.SetupController import get_children, update_setups
from app.controllers.UploadController import upload_default, upload_mt4
from app.controllers.utils import (
    from_db_to_df,
    from_df_to_db,
    parse_column_name,
    parse_column_type,
)
from app.models.Document import Document
from app.models.Setup import Setup
from app.models.User import User
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity

source_map = {
    "default": "Default",
    "mt4": "MT4",
}


def get_documents():
    """
    Retrieves All Documents
    """
    documents = []
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    files = Document.objects(author=user)
    for file in files:
        single_file = file.with_children()
        single_file["setups"] = get_children(single_file["id"])
        documents.append(single_file)
    response = jsonify(documents)
    return response


def get_document(file_id):
    """
    Retreives a Document state
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    file = Document.objects(id=file_id, author=user).get()
    # for col in state["schema"]["fields"]:
    #     col["title"] = parse_column_name(col.get("name"))
    #     col["field"] = col.pop("name")

    response = {"id": str(file.id), "name": file.name, "state": file.state}
    response = jsonify(response)
    return response


def get_document_columns(file_id):
    """
    Retrieves a Document columns
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    file = Document.objects(id=file_id, author=user).get()
    df = from_db_to_df(file.state)

    data_columns = df.dtypes
    columns = []
    for name, col_type in data_columns.items():
        columns.append(
            {
                "name": parse_column_name(name),
                "type": parse_column_type(col_type),
                "id": name,
            }
        )
    response = jsonify(columns)
    return response


def get_document_compare(file_id):
    """
    Retrieves a Document w/ Setups (compare)
    """
    id = get_jwt_identity()
    metric = request.args.get("metric", None)
    user = User.objects(id=id["$oid"]).get()
    setups = Setup.objects(author=user, documentId=file_id).order_by("-date_created")
    # implied that column names will not differ between setups and its document
    df = from_db_to_df(setups[0].state)
    metric_list = [col for col in df if re.match(r"col_[vpr]_", col)]
    metric = metric_list[0] if metric is None else metric

    setups_compared = []
    for setup in setups:
        current = setup.setup_compare(metric)
        current = json.loads(current)
        setups_compared.append(current)

    response = {
        "data": setups_compared,
        "metrics": [[metric, parse_column_name(metric)] for metric in metric_list],
        "active": parse_column_name(metric),
    }

    response = jsonify(response)
    return response


def get_calendar_table(document_id):
    """
    Returns a calendar view for a given document. As well as options and selected metric for result and date display.
    """
    metric = request.args.get("metric", None)
    date = request.args.get("date", None)
    document = Document.objects(id=document_id).get()
    df = from_db_to_df(document.state, orient="index")
    # TODO: combine both loops into a single
    metric_list = [col for col in df if re.match(r"col_[vpr]_", col)]
    # TODO: is it col_r or col_r_
    date_list = [col for col in df if col.startswith("col_d")]
    metric = metric_list[0] if metric is None else metric
    date = date_list[0] if date is None else date
    # Reset index to get the index column passed in to the JSON
    table = df.reset_index().to_json(orient="records")
    table = json.loads(table)
    response = {
        "table": table,
        "metrics": [[metric, parse_column_name(metric)] for metric in metric_list],
        "active_metric": metric,
        "active_date": date,
        "dates": [[date, parse_column_name(date)] for date in date_list],
    }

    response = jsonify(response)
    return response


def put_document(file_id):
    """Update Doucment"""
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get the document and its new name
    name = request.json.get("name", None)
    file = Document.objects(id=file_id, author=user).get()
    file.name = name
    file.save()
    return jsonify({"msg": "Document successfully updated", "success": True})


def post_document():
    """Upload Document"""
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get file
    file = request.files["file"]

    file_source = request.form.get("filesourcetype", None)

    # check if file exists
    is_file_exists = Document.objects(name=file.filename, author=user)
    if len(is_file_exists) > 0:
        return jsonify({"msg": "This file already exists", "success": False})
    try:
        if file_source == "default":
            df = upload_default(file)
        elif file_source == "mt4":
            df = upload_mt4(file)
        else:
            return jsonify(
                {"msg": "File source could not be identified", "success": False}
            )
    except UploadError as err:
        return jsonify({"msg": err.message, "success": False})

    # save the file to the DB
    document = Document(
        name=file.filename, author=user, state=df, source=source_map[file_source]
    )
    document.save()
    # save the default setup to the DB
    setup = Setup(
        name="Default", author=user, documentId=document, default=True, state=df
    )
    setup.save()

    return jsonify({"msg": "Document successfully uploaded", "success": True})


def clone_document(file_id):
    """
    Duplicates Existing File
    NOTE: It could be abstracted
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get the document and initialise a counter
    copy_counter = 1
    file = Document.objects(id=file_id).get()
    # get the path and the new name
    original = file.name
    new_name = original + " Copy_" + str(copy_counter)

    is_file_exists = Document.objects(name=new_name)
    while len(is_file_exists) > 0:
        copy_counter += 1
        new_name = original + " Copy_" + str(copy_counter)
        is_file_exists = Document.objects(name=new_name)

    new_df = from_df_to_db(from_db_to_df(file.state), add_index=True)
    # save the copy to the DB
    document = Document(name=new_name, author=user, state=new_df, source=file.source)
    document.save()
    # save the default setup to the DB
    setup = Setup(
        name="Default", author=user, documentId=document, default=True, state=new_df
    )
    setup.save()
    return jsonify({"msg": "Document successfully copied", "success": True})


def update_document(file_id):
    """
    Updates a Document by either: add, update or delete a given row

    INFO: this function could be abstracted
    """
    method = request.json.get("method", None)
    data = request.json.get("data", None)

    file = Document.objects(id=file_id).get()

    if method == "add":
        # create index for new row
        index = uuid.uuid4().hex
        # remove unnecessary keys from row
        data.pop("rowId", None)
        Document.objects(id=file_id).update(
            __raw__={"$set": {f"state.data.{index}": data}}
        )

    elif method == "update":
        index = data.get("rowId")
        # remove unnecessary keys from row
        data.pop("rowId", None)
        Document.objects(id=file_id).update(
            __raw__={"$set": {f"state.data.{index}": data}}
        )

    elif method == "delete":
        index = data.get("rowId")
        try:
            Document.objects(id=file_id).update_one(
                __raw__={"$unset": {f"state.data.{index}": 1}}
            )
        except Exception as err:
            return jsonify(
                {"msg": err, "success": False}
            )  # not sure this is good practice
    else:
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    try:
        update_setups(file.id)
    except Exception as err:
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    return jsonify({"msg": "Document updated correctly!", "success": True})


def delete_document(file_id):
    """
    Delete Document
    NOTE: make sure document belongs to the author
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get the document
    file = Document.objects(id=file_id, author=user).get()
    try:
        # delete setups
        Setup.objects(documentId=file.id).delete()
        # delete file in DB
        file.delete()
        return jsonify({"msg": "Document successfully deleted", "success": True})
    except:
        return jsonify({"msg": "Document does not exist", "success": False})
