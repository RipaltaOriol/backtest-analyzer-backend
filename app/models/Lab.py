from datetime import datetime
from bson.json_util import default
from mongoengine.document import DynamicDocument
from mongoengine.fields import DateField, DictField, ListField, ReferenceField, StringField
from app.models.User import User
from app.models.Document import Document

class Lab(DynamicDocument):
  name = StringField(default = 'undefined')
  state = DictField()
  filters = ListField()
  author = ReferenceField(User)
  documentId = ReferenceField(Document)
  date_created = DateField(default = datetime.utcnow)
  
  meta = {
    "collection": "labs",
    "ordering": ["-date_created"]
  }
