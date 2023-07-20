from datetime import datetime
from bson.json_util import default, dumps

from mongoengine.queryset import queryset_manager
from mongoengine.document import DynamicDocument
from mongoengine.fields import StringField, FloatField


class Template(DynamicDocument):
    name = StringField()
    description = StringField()
    price = FloatField()

    meta = {"collection": "templates"}
