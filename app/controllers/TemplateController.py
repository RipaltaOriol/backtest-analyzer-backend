import re

from app.controllers.utils import from_db_to_df, parse_column_name, parse_column_type
from app.models.Document import Document
from app.models.PPTTemplate import EntryPosition, PPTTemplate, TakeProfit
from app.models.Template import Template
from flask import jsonify, request


def fetch_template_mappings(document, user, document_state, mappings):

    # list of templates to insert
    templates = []

    # TODO: potential vectorization improvement
    # for prop, mapping in mappings.items():
    #     template[prop] = row[mapping] if

    for id, row in document_state["data"].items():
        try:
            template = PPTTemplate(
                author=user,
                document=document,
                row_id=id,
                # TODO: move this hard-coded value to a separate modules
                date_executed=row[mappings["date_executed"]]
                if mappings["date_executed"]
                else None,
                direction=row[mappings["direction"]] if mappings["direction"] else None,
                stop_loss=row[mappings["stop_loss"]] if mappings["stop_loss"] else None,
                asset=row[mappings["asset"]] if mappings["asset"] else None,
                return_percentage=row[mappings["return_percentage"]]
                if mappings["return_percentage"]
                else None,
                return_value=row[mappings["return_value"]]
                if mappings["return_value"]
                else None,
                take_profit=[
                    TakeProfit(
                        take_profit_number=0, take_profit=row[mappings["take_profit"]]
                    )
                ]
                if mappings["take_profit"]
                else [],
                positions=[
                    EntryPosition(
                        position_number=0,
                        order_type=row[mappings["order_type"]]
                        if mappings["order_type"]
                        else "Market",
                        price=row[mappings["price"]] if mappings["price"] else 0,
                        risk=0,
                        size=row[mappings["size"]] if mappings["size"] else 0,
                        risk_reward=row[mappings["risk_reward"]]
                        if mappings["risk_reward"]
                        else 0,
                    )
                ],
            )
            templates.append(template)

        except Exception as err:
            print("Error", err)  # log this error

    try:
        # TODO: warn user that all templats will be deleted to objtain the new mappings. In order workds, all progress will be lost.
        PPTTemplate.objects(document=document).delete()

        PPTTemplate.objects.insert(templates, load_bulk=False)
    except Exception as err:
        print("Failure", err)  # log this error

    return True


def assing_template_to_document(document_id, template_id):
    """
    Assigns a template to a document.
    """
    mappings = request.json.get("mappings", None)

    document = Document.objects(id=document_id).get()
    template = Template.objects(id=template_id).get()

    document.template = template

    is_mappings = any(mappings.values())

    # check if mapping is provided
    if is_mappings:
        document.template_mapping = mappings

    document.save()

    # TODO: setup templates
    # TODO: how does it know what tempalte uses this?
    # if mappings then perform the preliminary mapping (fetch)
    # TODO: problem if the account is empty
    if is_mappings:
        fetch_template_mappings(document, document.author, document.state, mappings)

    return jsonify(
        {
            "msg": "Template set successfully",
            "success": True,
        }
    )


def get_template_mapping(document_id):
    """Get a breakdown of column types and names to act as a template mapping helper"""
    document = Document.objects(id=document_id).get()

    columns = document.state["fields"]

    response = {
        "col_p": "col_p" in columns,
        "col_o": "col_o" in columns,
        "col_c": "col_c" in columns,
        "col_rr": "col_rr" in columns,
        "col_sl": "col_sl" in columns,
        "col_tp": "col_tp" in columns,
        "col_t": "col_t" in columns,
        "col_d": "col_d" in columns,
        "result": [col for col in columns if re.match(r"col_[vpr]_", col)],
        "dates": [col for col in columns if re.match(r"col_d_", col)],
        "other": [col for col in columns if re.match(r"col_m_", col)],
        # TODO: integrate the following types
        # order type
        # results (win, lose, etc)
        # direction ()
        # notes ()
    }
    return jsonify(response)
