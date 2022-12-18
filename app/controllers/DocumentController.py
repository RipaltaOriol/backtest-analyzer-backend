import json
import os
import shutil
from io import StringIO

import pandas as pd
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity

from app import app
from app.controllers.SetupController import get_children, update_setups
from app.controllers.UploadController import upload_default, upload_mt4
from app.controllers.utils import parse_column_name, parse_column_type
from app.models.Document import Document
from app.models.Setup import Setup
from app.models.User import User

source_map = {
    "default": "Default",
    "mt4": "MT4",
}

""" Retrieves All Documents
"""


def get_documents():
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


""" Retreives a Document state
"""


def get_document(file_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    file = Document.objects(id=file_id, author=user).get()
    state = file.state
    for col in state["schema"]["fields"]:
        col["title"] = parse_column_name(col.get("name"))
        col["field"] = col.pop("name")

    response = {"id": str(file.id), "name": file.name, "state": file.state}
    response = jsonify(response)
    return response


""" Retrieves a Document columns
"""


def get_document_columns(file_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    file = Document.objects(id=file_id, author=user).get()
    temp = json.dumps(file.state)
    data = pd.read_json(StringIO(temp), orient="table")
    data_columns = data.dtypes
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


""" Retrieves a Document w/ Setups (compare)
"""


def get_document_compare(file_id):
    id = get_jwt_identity()
    metric = request.args.get("metric", None)
    user = User.objects(id=id["$oid"]).get()
    setups = Setup.objects(author=user, documentId=file_id).order_by("-date_created")
    # implied that column names will not differ between setups and its document
    temp = json.dumps(setups[0].state)
    data = pd.read_json(StringIO(temp), orient="table")
    metric_list = [col for col in data if col.startswith(".r_")]
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


""" Update Doucment
"""


def put_document(file_id):
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get the document and its new name
    name = request.json.get("name", None)
    file = Document.objects(id=file_id, author=user).get()
    file.name = name
    file.save()
    return jsonify({"msg": "Document successfully updated", "success": True})


""" Upload Document
"""


def post_document():

    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get file
    file = request.files["file"]

    file_source = request.form.get("filesourcetype", None)

    # check if file exists
    is_file_exists = Document.objects(name=file.filename, author=user)
    if len(is_file_exists) > 0:
        return jsonify({"msg": "This file already exists", "success": False})

    if file_source == "default":
        df = upload_default(file)
    elif file_source == "mt4":
        df = upload_mt4(file)
    else:
        return jsonify({"msg": "File source could not be identified", "success": False})

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


""" Duplicates Existing File
    NOTE: It could be abstracted
"""


def clone_document(file_id):
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

    # save the copy to the DB
    document = Document(
        name=new_name, author=user, state=file.state, source=file.source
    )
    document.save()
    # save the default setup to the DB
    setup = Setup(
        name="Default", author=user, documentId=document, default=True, state=file.state
    )
    setup.save()
    return jsonify({"msg": "Document successfully copied", "success": True})


""" Updates an except document
"""


def update_document(file_id):
    method = request.json.get("method", None)
    data = request.json.get("data", None)

    file = Document.objects(id=file_id).get()
    # transform DictField to JSON string for Pandas to read
    temp = json.dumps(file.state)
    df = pd.read_json(StringIO(temp), orient="table")

    if method == "add":
        new_row = {i: data[i] for i in data if i not in {".d", "index", "tableData"}}
        df = df.append(new_row, ignore_index=True)

    elif method == "update":
        index = data.get("index")
        updated_row = {
            i: data[i] for i in data if i not in {".d", "index", "tableData"}
        }

        df.iloc[index] = updated_row

    elif method == "delete":

        index = data.get("index")
        try:
            print(df.iloc[index])
            df = df.drop([index + 1])
        except:
            print("Here")
            return jsonify({"msg": "This row does not exist.", "success": False})

    else:
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    df = df.to_json(orient="table")
    df = json.loads(df)
    file.modify(state=df)

    try:
        update_setups(file.id)
    except:
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    return jsonify({"msg": "Document updated correctly!", "success": True})


""" Delete Document
NOTE: make sure document belongs to the author
"""


def delete_document(file_id):
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
