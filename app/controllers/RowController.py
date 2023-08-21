from app.models.Document import Document
from app.models.PPTTemplate import PPTTemplate
from app.models.Setup import Setup
from flask import jsonify
from bson import ObjectId


def update_ppt_row(setup, row_id, row):
    """
    Update a setup row with PPT Template
    """

    # update _id to id
    row["id"] = ObjectId(row["_id"]["$oid"])
    row["author"] = ObjectId(row["author"]["$oid"])
    row["document"] = ObjectId(row["document"]["$oid"])
    row["setup"] = ObjectId(row["setup"]["$oid"])

    row.pop("_id")

    template = PPTTemplate.objects(row_id=row_id, setup=setup).get()
    template.update(**row)

    return jsonify({"msg": "Row updated correctly!", "success": True})


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
