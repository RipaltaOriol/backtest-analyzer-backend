from app.controllers.utils import parse_mappings, row_to_ppt_template
from app.models.Document import Document
from app.models.PPTTemplate import EntryPosition, PPTTemplate, TakeProfit
from app.models.Setup import Setup
from bson import ObjectId
from flask import jsonify


def update_ppt_row(document, row_id, row):
    """
    Update a setup row with PPT Template
    """
    try:
        # update _id to id
        row["id"] = ObjectId(row["_id"]["$oid"])
        row["author"] = ObjectId(row["author"]["$oid"])
        row["document"] = ObjectId(row["document"]["$oid"])
        # row["setup"] = ObjectId(row["setup"]["$oid"]) # not using setup - change structure!

        row.pop("_id")

        template = PPTTemplate.objects(row_id=row_id, document=document).get()

        template.update(**row)

        update_mappings_to_row(document, row, document.template_mapping)

        return jsonify({"msg": "Row updated correctly!", "success": True})

    except Exception as err:
        print("Something went wrong", err)
        return jsonify({"msg": "Something went wrong.", "success": False})


def update_default_row(setup, row_id, note, images, is_sync):
    """
    Update a setup row with Default Template
    """
    try:
        setup.update(__raw__={"$set": {f"state.data.{row_id}.note": note}})
        setup.update(__raw__={"$set": {f"state.data.{row_id}.imgs": images}})
        if is_sync:
            # update the parent document
            Document.objects(id=setup.documentId.id).update_one(
                __raw__={"$set": {f"state.data.{row_id}.note": note}}
            )
            Document.objects(id=setup.documentId.id).update_one(
                __raw__={"$set": {f"state.data.{row_id}.imgs": images}}
            )
            # update all the setups
            Setup.objects(documentId=setup.documentId).update(
                __raw__={"$set": {f"state.data.{row_id}.note": note}}
            )
            Setup.objects(documentId=setup.documentId).update(
                __raw__={"$set": {f"state.data.{row_id}.imgs": images}}
            )
    except Exception as err:
        return jsonify({"msg": err, "success": False})
    return jsonify({"msg": "Setup row updated correctly!", "success": True})


def update_mappings_to_row(document, row, mappings):
    """
    Update mapptings from a template to a row.
    """
    row_id = row["row_id"]
    state_item = document.state["data"][row_id]

    for template_k, state_k in mappings.items():
        if state_k:
            template_item = parse_mappings(row, template_k)
            state_item[state_k] = template_item

    document.update(__raw__={"$set": {f"state.data.{row_id}": state_item}})

    Setup.objects(documentId=document).update(
        __raw__={"$set": {f"state.data.{row_id}": state_item}}
    )

    return True


def update_mappings_to_template(document, id, row, method):
    """
    Update mapptings from a row to a template.
    """
    # TODO:
    # problem with this huge!
    # additioanlly I should make a transaction and only enter if all enter. Otherwise this creates weird write problems
    # also deal with broken message in the frontend (attempt to break it by setting a wrong data type on insertion)
    # this ticket should probably be part of data validation (big one xd)

    if method == "delete":
        PPTTemplate.objects(row_id=id, document=document).delete()

    if not document.template_mapping:
        return False

    if method == "add":
        template = PPTTemplate(
            author=document.author,
            document=document,
            row_id=id,
            take_profit=[TakeProfit(take_profit_number=0)],
            positions=[
                EntryPosition(
                    position_number=0,
                    order_type="Market",
                    price=0,
                    risk=0,
                    size=0,
                    risk_reward=0,
                )
            ],
        )

    elif method == "update":
        template = PPTTemplate.objects(row_id=id, document=document).get()

    else:
        return False

    template = row_to_ppt_template(document.template_mapping, template, row)

    template.save()

    return True


def generate_template(account, trade_id: str) -> PPTTemplate:
    return PPTTemplate(
        author=account.author,
        document=account,
        row_id=trade_id,
        take_profit=[TakeProfit(take_profit_number=0)],
        positions=[
            EntryPosition(
                position_number=0,
                order_type="Market",
                price=0,
                risk=0,
                size=0,
                risk_reward=0,
            )
        ],
    )


def delete_template(account, trade_id) -> None:
    PPTTemplate.objects(row_id=trade_id, document=account).delete()


def add_template(account, trade_id: str) -> None:
    try:
        template = generate_template(account, trade_id)
        template.save()
    except Exception as err:
        print("An error occurred: ", err)


def put_template(account, trade_id: str, trade: object) -> None:
    # NOTE: currently this fucntion only updates the mappings

    # check if template contains mappings
    if account.template_mapping:
        template = PPTTemplate.objects(row_id=trade_id, document=account).get()
        template = row_to_ppt_template(account.template_mapping, template, trade)
        template.save()
