from datetime import datetime

from mongoengine.document import DynamicDocument
from mongoengine.fields import DateField, ListField, StringField


class Filter(DynamicDocument):
    name = StringField()
    column = StringField()
    operation = StringField()
    value = ListField(default=list)
    date_created = DateField(default=datetime.utcnow)

    meta = {"collection": "filters", "ordering": ["-date_created"]}
