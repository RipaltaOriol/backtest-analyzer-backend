from datetime import datetime
from mongoengine.document import DynamicDocument
from mongoengine.fields import DateTimeField, ReferenceField, StringField, DictField
from app.models.User import User

class Document(DynamicDocument):
  name = StringField()
  author = ReferenceField(User)
  state = DictField()
  source = StringField()
  date_created = DateTimeField(default = datetime.utcnow)
  
  def with_children(self):
    document = {
      "id": str(self.id),
      "name": self.name,
      "source": self.source,
      'date': self.date_created
    }

    return document

  meta = {
    "collection": "documents",
    "indexes": ["name"],
    "ordering": ["-date_created"]
  }
