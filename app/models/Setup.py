import json
from datetime import datetime
from io import StringIO

import pandas as pd
from app.controllers.utils import from_db_to_df
from app.models.Document import Document
from app.models.Filter import Filter
from app.models.User import User
from bson.json_util import default, dumps
from mongoengine.document import DynamicDocument
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    DictField,
    ListField,
    ReferenceField,
    StringField,
)


class Setup(DynamicDocument):
    name = StringField(default="undefined")
    default = BooleanField()
    filters = ListField(ReferenceField(Filter), default=[])
    state = DictField()
    notes = StringField(default="")
    author = ReferenceField(User)
    documentId = ReferenceField(Document, reverse_delete_rule="CASCADE")
    date_created = DateTimeField(default=datetime.utcnow)

    def to_json(self):
        data = self.to_mongo()
        # rename key ID and Document ID
        data["id"] = str(self.id)
        data["documentId"] = str(self.documentId.id)
        data["date_created"] = self.date_created.isoformat()
        del data["_id"]

        # gets the Filter data instead of just the ID
        for i in range(len(data["filters"])):
            data["filters"][i] = {
                "id": str(self.filters[i].id),
                "name": self.filters[i].name,
            }
        return dumps(data)

    def setup_compare(self, metric):
        df = from_db_to_df(self.state)
        setup_compare = {
            "id": str(self.id),
            "name": self.name,
            "date_created": self.date_created.isoformat(),
            "filters": [str(filter.name) for filter in self.filters],
            "stats": {
                "data": [
                    ["Average", round(df[metric].mean(), 2)],
                    ["Total", round(df[metric].sum(), 2)],
                ]
            },
            "breakdown": {
                "labels": ["Winners", "Break-Even", "Lossers"],
                "values": [
                    len(df[df[metric] > 0]),
                    len(df[df[metric] == 0]),
                    len(df[df[metric] < 0]),
                ],
            },
        }

        return json.dumps(setup_compare)

    meta = {"collection": "setups", "ordering": ["-date_created"]}
