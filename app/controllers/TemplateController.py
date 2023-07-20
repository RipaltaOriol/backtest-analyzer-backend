from app.models.Document import Document
from app.models.Template import Template
from flask import jsonify


def assing_template_to_document(document_id, template_id):
    """
    Assigns a template to a document.
    """
    document = Document.objects(id=document_id).get()
    template = Template.objects(id=template_id).get()
    document.template = template
    document.save()
    return jsonify(
        {
            "msg": "Template set successfully",
            "success": True,
        }
    )
