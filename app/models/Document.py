from datetime import datetime
from mongoengine.document import DynamicDocument
from mongoengine.fields import DateTimeField, ReferenceField, StringField
from app.models.User import User

class Document(DynamicDocument):
  title = StringField()
  path = StringField()
  author = ReferenceField(User)
  date_created = DateTimeField(default = datetime.utcnow)
  
  meta = {
    "collection": "documents",
    "indexes": ["title"],
    "ordering": ["-date_created"]
  }
