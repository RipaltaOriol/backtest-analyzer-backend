from datetime import datetime
from bson.json_util import default
from mongoengine.document import DynamicDocument
from mongoengine.fields import DateTimeField, BooleanField, ListField, ReferenceField, StringField
from app.models.User import User
from app.models.Document import Document


class Setup(DynamicDocument):
    name = StringField(default = 'undefined')
    default = BooleanField()
    filters = ListField()
    state = StringField()
    notes = StringField(default = '')
    author = ReferenceField(User)
    documentId = ReferenceField(Document)
    date_created = DateTimeField(default = datetime.utcnow)

    meta = {
        "collection": "setups",
        "ordering": ["-date_created"]
    }

