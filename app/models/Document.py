from datetime import datetime
from mongoengine.document import DynamicDocument
from mongoengine.fields import DateTimeField, ReferenceField, StringField, DictField
from app.models.User import User

class Document(DynamicDocument):
  name = StringField()
  author = ReferenceField(User)
  state = DictField()
  date_created = DateTimeField(default = datetime.utcnow)
  
  meta = {
    "collection": "documents",
    "indexes": ["name"],
    "ordering": ["-date_created"]
  }
