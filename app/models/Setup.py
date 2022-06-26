from datetime import datetime
from bson.json_util import default, dumps
from mongoengine.document import DynamicDocument
from mongoengine.fields import DateTimeField, BooleanField, ListField, ReferenceField, StringField

from app.models.User import User
from app.models.Document import Document
from app.models.Filter import Filter

class Setup(DynamicDocument):
    name = StringField(default = 'undefined')
    default = BooleanField()
    filters = ListField(ReferenceField(Filter), default = [])
    state = StringField()
    notes = StringField(default = '')
    author = ReferenceField(User)
    documentId = ReferenceField(Document)
    date_created = DateTimeField(default = datetime.utcnow)

    def to_json(self):
        data = self.to_mongo()
        # gets the Filter data instead of just the ID
        for i in range(len(data['filters'])):
            data['filters'][i]= self.filters[i].to_mongo()
        return dumps(data)

    meta = {
        "collection": "setups",
        "ordering": ["-date_created"]
    }

