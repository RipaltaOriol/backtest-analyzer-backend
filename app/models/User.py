import json
from datetime import datetime
from mongoengine.document import Document
from mongoengine.fields import DateField, EmailField, StringField

class User(Document):
  email = EmailField(unique = True, required = True)
  password = StringField(required = True)
  date_created = DateField(default = datetime.utcnow)

  def json(self):
    user_dict = {
      "email": self.email,
      "password": self.password,
      "date_created": self.date_created
    }
    return json.dumbps(user_dict)

  meta = {
    "collection": "users",
    "indexes": ["email"],
    "ordering": ["-date_created"]
  }


