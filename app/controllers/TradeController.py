import uuid

from app.controllers.RowController import add_template, delete_template, put_template
from app.controllers.SetupController import update_setups
from app.controllers.utils import from_db_to_df, validation_pipeline
from app.models.Document import Document
from flask import jsonify, request


def delete_trade(account_id, trade_id):
    account = Document.objects(id=account_id).get()
    try:
        account.modify(__raw__={"$unset": {f"state.data.{trade_id}": 1}})
    except Exception as err:
        return jsonify({"msg": "Something went wrong.", "success": False})

    if account.template:
        template_name = account.template.name
        if template_name == "PPT":
            delete_template(account, trade_id)

    try:
        document_df = from_db_to_df(account.state)
        update_setups(account.id, document_df)
    except Exception as err:
        print("Something went wrong:", err)
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    return jsonify({"msg": "Trade delete successfully!", "success": True})


def post_trade(account_id):
    account = Document.objects(id=account_id).get()
    trade_id = uuid.uuid4().hex
    trade = {"note": "", "imgs": ""}

    try:
        account.modify(__raw__={"$set": {f"state.data.{trade_id}": trade}})
        if account.template:
            template_name = account.template.name
            if template_name == "PPT":
                add_template(account, trade_id)
    except Exception as err:
        return jsonify({"msg": "Something went wrong.", "success": False})

    try:
        document_df = from_db_to_df(account.state)
        update_setups(account.id, document_df)
    except Exception as err:
        print("Something went wrong:", err)
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    # TODO: return ID of account created
    trade["rowId"] = trade_id
    return jsonify(
        {"msg": "Trade added successfully!", "success": True, "trade": trade}
    )


def put_trade(account_id, trade_id):
    account = Document.objects(id=account_id).get()

    trade = request.json.get("trade", None)
    try:
        trade = validation_pipeline(trade)

        # TODO: double check if this is necesary
        # remove unnecessary keys from row
        trade.pop("rowId", None)

        account.modify(__raw__={"$set": {f"state.data.{trade_id}": trade}})

        if account.template:
            template_name = account.template.name
            if template_name == "PPT":
                # TODO: handle PPT update (currently only mapping fields)
                put_template(account, trade_id, trade)

    except Exception as err:
        return jsonify({"msg": "Something went wrong.", "success": False})

    try:
        document_df = from_db_to_df(account.state)
        update_setups(account.id, document_df)
    except Exception as err:
        print("Something went wrong:", err)
        return jsonify({"msg": "Something went wrong. Try again!", "success": False})

    return jsonify({"msg": "Trade updated successfully!", "success": True})
