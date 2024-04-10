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
from app.controllers.FilterController import filter_open_trades
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
    validation_pipeline,
)
from app.models.Document import Document, TradeCondition
from app.models.Setup import Setup
from app.models.Template import Template
from app.models.User import User
from app.services.MT4_api import (
    connect_account,
    discover_server_ip,
    get_account_history,
)
from bson import DBRef, ObjectId, json_util
from flask import jsonify, request
from flask.wrappers import Response
from flask_jwt_extended import get_jwt_identity

source_map = {
    "DEFAULT": "Default",
    "MT4_FILE": "MT4 File",
    "MT4_API": "MT4 API",
    "MT5_API": "MT5 API",
}

OTHER_COLUMNS_TYPE_MAPPING = {
    "col_p": "object",
    "col_o": "float",
    "col_c": "float",
    "col_rr": "float",
    "col_sl": "float",
    "col_tp": "float",
    "col_t": "object",
    "col_d": "object",
}


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

    # check if file exists
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
            df_columns[column] = pd.Series(
                dtype=OTHER_COLUMNS_TYPE_MAPPING.get(column, "object")
            )

    df = pd.DataFrame(df_columns)

    # df = _add_required_columns(df) # see what happens if this is added
    data = from_df_to_db(df, add_index=True)
    state = {"data": data, "fields": df.dtypes.apply(lambda x: x.name).to_dict()}

    # get default tempalte
    default_template = Template.objects(name="Default").get()

    # save the file to the DB
    document = Document(
        name=name, author=user, state=state, source="Manual", template=default_template
    )
    document.save()
    # save the default setup to the DB
    setup = Setup(
        name="Default", author=user, documentId=document, default=True, state=state
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
    account_columns = file.state["fields"]

    # TODO: check if DataFrame is emtpy. If it is then get data from elsewhere (create utils function).
    account_columns = {
        id: {"name": parse_column_name(id), "type": type, "column": id[0:6]}
        for id, type in account_columns.items()
    }

    response = jsonify(account_columns)
    return response


def put_document_columns(account_id):
    """
    Updates the account columns
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()

    account = Document.objects(id=account_id, author=user).get()
    columns = request.json

    template_columns = (
        [*account.template_mapping.values()] if account.template_mapping else []
    )

    failure_to_update = []

    fields = account.state.get("fields")
    field_names = [*fields.keys()]
    df = from_db_to_df(account.state)
    for to_delete_column in columns.pop("to_delete", []):
        # checks column is not used in templates
        if to_delete_column in template_columns:
            failure_to_update.append(to_delete_column)
            continue

        df = df.drop(to_delete_column, axis=1, errors="ignore")
        del fields[to_delete_column]

    for column_name, props in columns.items():
        action = props.get("action")
        if action == "add":
            # check column does not exist
            if column_name in field_names:
                failure_to_update.append(column_name)
            else:
                new_type = props.get("type", None)
                expected_type = get_columm_expected_type(column_name, new_type)

                fields[column_name] = expected_type
                df[column_name] = None

        elif action == "edit":
            # check column does not exist and is not being used in templates
            if column_name in template_columns or column_name not in field_names:
                failure_to_update.append(column_name)
                continue
            try:
                new_column = props.get("new_column")
                new_type = props.get("type", None)

                expected_type = get_columm_expected_type(new_column, new_type)

                df[column_name] = (
                    df[column_name]
                    .astype(expected_type)
                    .where(df[column_name].notnull(), None)
                )
                df.rename(columns={column_name: new_column}, inplace=True)

                del fields[column_name]
                fields[new_column] = expected_type

            except Exception as err:
                failure_to_update.append(column_name)
                print("Something went wrong: ", err)

    # check if account contains a result
    if not [column for column in df.columns if re.match(r"col_[vpr]_", column)]:
        return jsonify(
            {"success": False, "msg": "At least one result property is required!"}
        )

    data = from_df_to_db(df)
    account.update(__raw__={"$set": {f"state": {"fields": fields, "data": data}}})

    try:
        # TODO: not all filters have to be removed
        update_setups(
            account.id,
            df,
            document_fields=fields,
            wiht_fields=True,
            remove_filters=True,
        )
    except Exception as err:
        print("Something went wrong: ", err)
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    if failure_to_update:
        parse_columns = ", ".join(
            [parse_column_name(column) for column in failure_to_update]
        )
        return jsonify({"success": False, "msg": f"Fail to update: {parse_columns}"})

    return jsonify(
        {"success": True, "msg": "Account fields have been updated correctly!"}
    )


def get_columm_expected_type(column, type_specification=None):
    # TODO: move this into utils
    # TODO: potential issue here
    if column.startswith("col_m_"):
        return type_specification
    elif column.startswith("col_d_"):
        return "datetime64[ns, utc]"
    elif column == "col_d" or column == "col_p" or column == "col_t":
        return "object"
    else:
        return "float64"


def get_account_settings(account_id):
    account = Document.objects(id=account_id).get()

    return jsonify(
        {
            "name": account.name,
            "balance": account.balance,
            "currency": account.account_currency.value
            if account.account_currency
            else None,
            "positionCondition": {
                "column": account.open_conditions[0].column
                if account.open_conditions
                else None,
                "condition": account.open_conditions[0].condition
                if account.open_conditions
                else None,
                "value": account.open_conditions[0].value
                if account.open_conditions
                else None,
            },
        }
    )


def put_account_settings(account_id) -> Response:
    """
    Updates an account's settings based on provided JSON payload. Settings can include the account's
    name, balance, currency, and conditions for opening trades. If an open trade condition is specified,
    it validates and applies this condition. Then, it updates the account's general settings.

    Parameters:
    - account_id (str): Unique identifier of the account to update.

    Returns:
    - Flask.Response: JSON response indicating the outcome.
    """
    account = Document.objects(id=account_id).get()

    name = request.json.get("name", account.name)
    balance = request.json.get("balance", account.balance)
    currency = request.json.get(
        "currency", account.account_currency.value if account.account_currency else None
    )
    open_condition = request.json.get("openCondition", None)

    try:
        if open_condition:
            # Extract open condition values from request
            open_column = open_condition.get("column", None)
            open_operation = open_condition.get("condition", None)
            open_value = open_condition.get("value", None)

            if open_column and open_operation:

                if (
                    open_operation == "empty" or open_operation == "not_empty"
                ) or open_value:
                    # Ensure filter condition does not return an error
                    df = from_db_to_df(account.state)
                    column_type = account.state["fields"].get(open_column)
                    filter_open_trades(
                        df, open_column, column_type, open_operation, open_value
                    )

                    open_trade_condition = TradeCondition(
                        column=open_column,
                        condition=open_operation,
                        value=open_value,
                    )

                    account.modify(open_conditions=[open_trade_condition])

    except Exception as error:
        # TODO: log
        return jsonify(
            {
                "message": "There was an error setting up condition for open positions. Please try again.",
                "success": False,
            }
        )

    try:
        # Validate balance is a number
        balance = float(balance)
        account.modify(name=name, balance=balance, account_currency=currency)
        return jsonify(
            {"message": "Account settings updated successfully!", "success": True}
        )
    except Exception as e:
        return jsonify(
            {"message": "Something went wrong. Please try again.", "success": False}
        )


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
        if file_source == "DEFAULT":
            df = upload_default(file)
        elif file_source == "MT4_FILE":
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

    new_df = from_db_to_df(file.state)
    new_data = from_df_to_db(new_df, add_index=True)
    new_state = {
        "data": new_data,
        "fields": new_df.dtypes.apply(lambda x: x.name).to_dict(),
    }

    # save the copy to the DB
    document = Document(name=new_name, author=user, state=new_state, source=file.source)
    document.save()
    # save the default setup to the DB
    setup = Setup(
        name="Default", author=user, documentId=document, default=True, state=new_state
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

    data = validation_pipeline(data)

    document = Document.objects(id=file_id).get()
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

    if document.template:
        template_type = document.template.name

    if template_type == "PPT":
        update_mappings_to_template(document, index, data, method)

    try:
        document = Document.objects(id=file_id).first()
        document_df = from_db_to_df(document.state)
        update_setups(document.id, document_df)
    except Exception as err:
        print("Something went wrong", err)
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


async def fetch_metatrader():
    """
    Fetch account directly from MetaTrader. It requires account, passsword, server and platform.
    """
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()

    account = request.json.get("account", None)
    password = request.json.get("password", None)
    server = request.json.get("server", None)
    platform = request.json.get("platform", None)

    if not account and not password and not server and not platform:
        return jsonify({"msg": "Some information is missing.", "success": False})

    # ensure no duplicate accounts are created
    is_file_exists = Document.objects(name=f"{account}+{server}", author=user)
    if len(is_file_exists) > 0:
        return jsonify({"msg": "This file already exists", "success": False})

    server_ips = discover_server_ip(server, platform)
    if server_ips.get("success"):
        # TODO: ideally one wil try multiple API
        ip = server_ips.get("server_ips")[0]

        connection_string = connect_account(int(account), password, ip, platform)
        account_history = get_account_history(connection_string, platform)

        if account_history.get("success"):
            print(account_history.get("account_history"))
            state = upaload_meta_api(account_history.get("account_history"))
            default_template = Template.objects(name="Default").get()

            # TODO: is probably better not to store this information
            account = Document(
                name=f"{account}+{server}",
                author=user,
                state=state,
                source=source_map.get(platform),
                template=default_template,
                metaapi_id=connection_string,
                meta_account=account,
                meta_password=password,
                meta_server=server,
            )
            account.save()

            # create an initial setup for the account
            setup = Setup(
                name="Default",
                author=user,
                documentId=account,
                default=True,
                state=state,
            )
            setup.save()

            return jsonify({"msg": "Account successfully extracted!", "success": True})

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

    # id = get_jwt_identity()
    # user = User.objects(id=id["$oid"]).get()
    # # get credentials
    # file = Document.objects(id=file_id, author=user).get()
    # # get meta trader account
    # meta_account = await create_meta_account(
    #     file.meta_account, file.meta_password, file.meta_server
    # )

    # if not meta_account["success"]:
    #     return jsonify(
    #         {"msg": "Something went wrong. Try again later.", "success": False}
    #     )

    # df = upaload_meta_api(meta_account["deals"])

    # file.state = df
    # file.metaapi_id = meta_account["account_id"]
    # file.save()

    # try:
    #     update_setups(file.id)
    # except Exception as err:
    #     return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    return jsonify({"msg": "Document updated correctly!", "success": True})
