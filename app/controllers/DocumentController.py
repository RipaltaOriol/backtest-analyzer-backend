import asyncio
import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
from app import app
from app.controllers.errors import UploadError
from app.controllers.RowController import update_mappings_to_template
from app.controllers.SetupController import get_children, update_setups
from app.controllers.UploadController import (
    upaload_meta_api,
    upload_default,
    upload_mt4,
)
from app.controllers.utils import (
    from_db_to_df,
    from_df_to_db,
    parse_column_name,
    parse_column_type,
)
from app.models.Document import Document
from app.models.Setup import Setup
from app.models.Template import Template
from app.models.User import User
from bson import DBRef, ObjectId, json_util
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity

# from metaapi_cloud_sdk import MetaApi
# from metaapi_cloud_sdk.clients.metaApi.metatraderAccount_client import (
#     NewMetatraderAccountDto,
# )

source_map = {"default": "Default", "mt4_file": "MT4 File", "mt4_api": "MT4 API"}


def get_documents():
    """
    Retrieves All Documents
    """

    pipeline = [
        {
            "$lookup": {
                "from": Setup._get_collection_name(),
                "localField": "_id",
                "foreignField": "documentId",
                "as": "setups",
            }
        },
        {
            "$lookup": {
                "from": Template._get_collection_name(),
                "localField": "template",
                "foreignField": "_id",
                "as": "template",
            }
        },
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "name": 1,
                "source": 1,
                "template": {
                    "$let": {
                        "vars": {"firstTemplate": {"$arrayElemAt": ["$template", 0]}},
                        "in": {
                            "name": "$$firstTemplate.name",
                            "id": {"$toString": "$$firstTemplate._id"},
                        },
                    }
                },
                "date": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": {"$toDate": "$date_created"},
                    }
                },
                "setups": {
                    "$map": {
                        "input": "$setups",
                        "as": "setup",
                        "in": {
                            "id": {"$toString": "$$setup._id"},
                            "name": "$$setup.name",
                            "isDefault": "$$setup.default",
                            "date": {
                                "$dateToString": {
                                    "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                                    "date": {"$toDate": "$$setup.date_created"},
                                }
                            },
                        },
                    }
                },
            }
        },
    ]

    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    documents = Document.objects(author=user).aggregate(pipeline)
    documents = json.loads(json_util.dumps(documents))
    return jsonify(documents)


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


def create_document():
    """
    Creates a new Document
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()

    name = request.json.get("name", None)
    columns = request.json.get("fields", None)
    other = request.json.get("checkbox", None)

    # # check if file exists
    is_file_exists = Document.objects(name=name, author=user)
    if len(is_file_exists) > 0:
        return jsonify({"msg": "This file already exists", "success": False})

    df_columns = {}

    for column in columns:
        dtype = pd.Series(dtype="object")
        if column["value"].startswith("col_m_"):
            dtype = pd.Series(dtype=column["dtype"])
        elif column["value"].startswith("col_d_"):
            dtype = pd.Series(dtype="datetime64[ns, utc]")
        else:
            dtype = pd.Series(dtype="float")
        df_columns[f"{column['value']}{column['name']}"] = dtype

    for column, is_add in other.items():
        if is_add:
            df_columns[column] = pd.Series(dtype="object")

    df = pd.DataFrame(df_columns)

    # df = _add_required_columns(df) # see what happens if this is added
    df = from_df_to_db(df, add_index=True)
    # get default tempalte
    default_template = Template.objects(name="Default").get()

    # save the file to the DB
    document = Document(
        name=name, author=user, state=df, source="Manual", template=default_template
    )
    document.save()
    # save the default setup to the DB
    setup = Setup(
        name="Default", author=user, documentId=document, default=True, state=df
    )
    setup.save()
    return jsonify({"msg": "Document successfully uploaded", "success": True})


def get_document_columns(file_id):
    """
    Retrieves a Document columns
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    file = Document.objects(id=file_id, author=user).get()
    df = from_db_to_df(file.state)
    columns = []
    data_columns = file.state["fields"]

    # check if DataFrame is emtpy. If it is then get data from elsewhere (create utils function).
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
    if not metric_list:
        return jsonify(
            {
                "msg": "Insufficient data to compare",
                "success": False,
            }
        )
    metric = metric_list[0] if metric is None else metric

    setups_compared = []
    for setup in setups:
        current = setup.setup_compare(metric)
        current = json.loads(current)
        setups_compared.append(current)

    response = {
        "success": True,
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
    table = df.reset_index().to_json(orient="records", date_format="iso")
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
        elif file_source == "mt4_file":
            df = upload_mt4(file)
        else:
            return jsonify(
                {"msg": "File source could not be identified", "success": False}
            )
    except UploadError as err:
        return jsonify({"msg": err.message, "success": False})

    # save the file to the DB
    default_template = Template.objects(name="Default").get()
    document = Document(
        name=file.filename,
        author=user,
        state=df,
        source=source_map[file_source],
        template=default_template,
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


def put_document_row(file_id):
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

    template_type = None

    if file.template:
        template_type = file.template.name

    if template_type == "PPT":
        update_mappings_to_template(file, index, data, method)

    try:
        # TODO: this does not look like a great solution
        # TODO: the code inside it does not look like it's efficient - overkill for what I'm looking to achieve
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


async def create_meta_account(account: str, password: str, server: str):
    """
    Create a MT4 account on MetaApi
    """

    token = os.getenv("METAAPI_TOKEN")
    return {"success": False}
    # api = MetaApi(token)
    # print(token, api)
    # try:
    #     new_account = NewMetatraderAccountDto(
    #         magic=123456,
    #         login=account,
    #         name=f"{account}+{server}",
    #         password=password,
    #         server=server,
    #         platform="mt4",
    #         type="cloud-g1",
    #         keywords=[server],
    #     )

    #     # alternatively one could also connect through account_id
    #     account = await api.metatrader_account_api.create_account(new_account)

    #     initial_state = account.state
    #     deployed_states = ["DEPLOYING", "DEPLOYED"]

    #     if initial_state not in deployed_states:
    #         #  wait until account is deployed and connected to broker
    #         await account.deploy()

    #     print(
    #         "Waiting for API server to connect to broker (may take couple of minutes)"
    #     )
    #     await account.wait_connected()

    #     # connect to MetaApi API
    #     connection = account.get_rpc_connection()
    #     await connection.connect()

    #     # TODO: this step break the code
    #     # wait until terminal state synchronized to the local state
    #     # print('Waiting for SDK to synchronize to terminal state (may take some time depending on your history size)')
    #     # await connection.wait_synchronized()

    #     # invoke RPC API (replace ticket numbers with actual ticket numbers which exist in your MT account)
    #     # get account deals for the last 10 years
    #     days = 365 * 10
    #     trade_history = await connection.get_deals_by_time_range(
    #         datetime.utcnow() - timedelta(days=days), datetime.utcnow()
    #     )

    #     # close connnection and remove account
    #     await connection.close()

    #     # TODO: I could also delete account here

    #     return {
    #         "deals": trade_history["deals"],
    #         "account_id": account.id,
    #         "success": True,
    #     }
    # except Exception as err:
    #     if (
    #         str(err)
    #         == "Free subscription plan allows you to create no more than 2 trading accounts for personal use free of charge"
    #     ):
    #         try:
    #             all_accounts = await api.metatrader_account_api.get_accounts()
    #             account_to_delete = all_accounts[0]
    #             print(account_to_delete)

    #             await account_to_delete.remove()
    #             await account_to_delete.wait_removed()
    #             return await create_meta_account(account, password, server)
    #         except Exception as err:
    #             return {"success": False}

    #     return {"success": False}


async def fetch_metatrader():
    """
    Fetch account directly from MetaTrader. It requires account, passsword, server and platform.
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()

    account = request.json.get("account", None)
    password = request.json.get("password", None)
    server = request.json.get("server", None)

    # check if file exists
    is_file_exists = Document.objects(name=f"{account}+{server}", author=user)
    if len(is_file_exists) > 0:
        return jsonify({"msg": "This file already exists", "success": False})

    meta_account = await create_meta_account(account, password, server)

    if meta_account["success"]:

        df = upaload_meta_api(meta_account["deals"])
        default_template = Template.objects(name="Default").get()

        # TODO: is probably better not to store this information
        document = Document(
            name=f"{account}+{server}",
            author=user,
            state=df,
            source="MT4 API",
            template=default_template,
            metaapi_id=meta_account["account_id"],
            meta_account=account,
            meta_password=password,
            meta_server=server,
        )
        document.save()

        # save the default setup to the DB
        setup = Setup(
            name="Default", author=user, documentId=document, default=True, state=df
        )
        setup.save()

        return jsonify({"msg": "Document successfully uploaded", "success": True})

    else:
        return jsonify(
            {"msg": "Something went wrong. Try again later.", "success": False}
        )


async def refetch_document(file_id):
    """ "
    Refetches a Document and updates it
    """

    # TODO: this could be done better by only adding the new deals.
    # TODO: this could be improved by checking if account it is still active

    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()
    # get credentials
    file = Document.objects(id=file_id, author=user).get()
    # get meta trader account
    meta_account = await create_meta_account(
        file.meta_account, file.meta_password, file.meta_server
    )

    if not meta_account["success"]:
        return jsonify(
            {"msg": "Something went wrong. Try again later.", "success": False}
        )

    df = upaload_meta_api(meta_account["deals"])

    file.state = df
    file.metaapi_id = meta_account["account_id"]
    file.save()

    try:
        update_setups(file.id)
    except Exception as err:
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    return jsonify({"msg": "Document updated correctly!", "success": True})
