import json
import logging
import re
import uuid

import pandas as pd
from app import app
from app.controllers.errors import UploadError
from app.controllers.FilterController import filter_open_trades
from app.controllers.RowController import update_mappings_to_template
from app.controllers.SetupController import update_setups
from app.controllers.UploadController import upload_default, upload_mt4
from app.controllers.utils import (
    from_db_to_df,
    from_df_to_db,
    get_columm_expected_type,
    parse_column_name,
    validation_pipeline,
)
from app.models.Document import Document, TradeCondition
from app.models.Setup import Setup
from app.models.Template import Template
from app.models.User import User
from app.repositories.version_repository import VersionRepository
from app.services.account_manager import AccountManager
from app.services.filter_service import FilterService
from app.services.version_service import VersionService
from bson import json_util
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
    # TODO: some logic here can be abstracted
    id = get_jwt_identity()
    user = User.objects(id=id["$oid"]).get()

    account = Document.objects(id=account_id, author=user).first()

    if not account:
        return jsonify(
            {"success": False, "msg": "Account not found. Please try again."}
        )

    add_columns = request.json.get("add", [])
    edit_columns = request.json.get("edit", [])
    delete_columns = request.json.get("delete", [])

    # Get state of the account
    df = from_db_to_df(account.state)

    # Get columns mapped to a template
    template_columns = (
        list(account.template_mapping.values()) if account.template_mapping else []
    )

    # Extract account columns (fields)
    fields = account.state.get("fields")
    account_fields = list(fields.keys())

    # Track filters to remove
    filters_to_remove = []

    try:
        # Handle columns to delete
        for column in delete_columns:
            # Validates column is not used within templates
            if column in template_columns:
                return jsonify(
                    {
                        "success": False,
                        "msg": f"Column {parse_column_name(column)} cannot be deleted becuase it's used in a template. Modify your template settings to delete this column.",
                    }
                )
            df = df.drop(column, axis=1, errors="ignore")
            del fields[column]
            filters_to_remove.append(column)

        # Handle columns to add
        for column in add_columns:
            column_id = column["column"]
            column_name = column_id + column["name"]
            if column_name in account_fields:
                return jsonify(
                    {
                        "success": False,
                        "msg": f"Column {parse_column_name(column_name)} cannot be added because it already exists.",
                    }
                )
            # Set the column type
            column_type = column.get("type", None)
            column_type = get_columm_expected_type(column_id, column_type)

            fields[column_name] = column_type
            df[column_name] = None

        # Handle columns to edit
        for column in edit_columns:
            column_id = column["column"]
            new_column_name = column["new_name"]
            pre_column_name = column["prev_name"]

            # Validates column is not used within templates but exists
            if (
                pre_column_name in template_columns
                or pre_column_name not in account_fields
            ):
                return jsonify(
                    {
                        "success": False,
                        "msg": f"Column {parse_column_name(pre_column_name)} cannot be edited because it is used in a template or does not exist.",
                    }
                )

            # Set the column type
            column_type = column.get("type", None)
            column_type = get_columm_expected_type(new_column_name, column_type)

            df[pre_column_name] = (
                df[pre_column_name]
                .astype(column_type)
                .where(df[pre_column_name].notnull(), None)
            )
            df.rename(columns={pre_column_name: new_column_name}, inplace=True)

            del fields[pre_column_name]
            fields[new_column_name] = column_type
            filters_to_remove.append(pre_column_name)

    except Exception as e:
        # TODO: this exception could be more specific on what column failed
        logging.error(
            f"Error updating columns for account {account_id}: {str(e)}"
        )  # TODO: IMPROVE THIS MESSAGE
        return jsonify(
            {
                "success": False,
                "msg": "Failed to update account columns. Please try again.",
            }
        )

    # Ensure a result column is present for the account
    if not [column for column in df.columns if re.match(r"col_[vpr]_", column)]:
        return jsonify(
            {
                "success": False,
                "msg": "At least one result column is required for an account.",
            }
        )

    # Update document and its state
    data = from_df_to_db(df)
    account.update(__raw__={"$set": {f"state": {"fields": fields, "data": data}}})

    try:
        # TODO: this should not be here (performance related)
        version_repository = VersionRepository()
        filter_service = FilterService()
        version_service = VersionService(version_repository, filter_service)

        version_service.update_version_from_account_without_filters(
            account.id, df, fields, filters_to_remove
        )

    except Exception as error:
        logging.error(
            f"Failed to update setups on ${account_id} during a column update. Error: ${str(error)}"
        )
        return jsonify(
            {"msg": "Something went wrong. Please try again.", "success": False}
        )

    return jsonify({"success": True, "msg": "The account was successfully modified!"})


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
                        value=str(open_value),
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
    except UploadError as error:
        logging.exception(f"File failed to upload: ${file.filename}. Error: ${error}")
        return jsonify({"msg": error.message, "success": False})

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
    except Exception as error:
        logging.error(f"Failed to update setups on ${file_id}. Error: ${error}")
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

    # Check all variables exist
    if not all([account, password, server, platform]):
        return jsonify({"msg": "Some information is missing.", "success": False})

    account_manager = AccountManager(user)
    result = account_manager.fetch_from_metatrader(account, password, server, platform)
    return jsonify(result)


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

    # df = upload_meta_api(meta_account["deals"])

    # file.state = df
    # file.metaapi_id = meta_account["account_id"]
    # file.save()

    # try:
    #     update_setups(file.id)
    # except Exception as err:
    #     return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    return jsonify({"msg": "Document updated correctly!", "success": True})
