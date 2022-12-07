import json
import pandas as pd
from io import StringIO
from datetime import datetime
from bson.json_util import default, dumps
from mongoengine.document import DynamicDocument
from mongoengine.fields import DateTimeField, BooleanField, ListField, ReferenceField, StringField, DictField

from app.models.User import User
from app.models.Document import Document
from app.models.Filter import Filter

class Setup(DynamicDocument):
    name = StringField(default = 'undefined')
    default = BooleanField()
    filters = ListField(ReferenceField(Filter), default = [])
    state = DictField()
    notes = StringField(default = '')
    author = ReferenceField(User)
    documentId = ReferenceField(Document, reverse_delete_rule="CASCADE")
    date_created = DateTimeField(default = datetime.utcnow)

    def to_json(self):
        data = self.to_mongo()
        # rename key ID and Document ID
        data['id'] = str(self.id)
        data['documentId'] = str(self.documentId.id)
        data['date_created'] = self.date_created.isoformat()
        del data['_id']

        # gets the Filter data instead of just the ID
        for i in range(len(data['filters'])):
            data['filters'][i]= {
                'id': str(self.filters[i].id),
                'name': self.filters[i].name
            }
        return dumps(data)
    
    def setup_compare(self, metric):
        temp = json.dumps(self.state)
        data = pd.read_json(StringIO(temp), orient = 'table')
        result_columns = [col for col in data if col.startswith('.r_')]



        setup_compare = {
            "id": str(self.id),
            "name": self.name,
            "date_created": self.date_created.isoformat(),
            "filters": [str(filter.name) for filter in self.filters],
            "stats": {
                # "headers": [col[3:] for col in result_columns],
                "data": [
                    ['Average', round(data[metric].mean(), 2)],
                    ['Total', round(data[metric].sum(), 2)]
                ]
            },
            "breakdown": {
                'labels': ['Winners', 'Break-Even', 'Lossers'],
                'values': [
                    len(data[data[metric] > 0]),
                    len(data[data[metric] == 0]),
                    len(data[data[metric] < 0])
                ]
            }
        }

        return json.dumps(setup_compare)#, default=json_util.default)


    meta = {
        "collection": "setups",
        "ordering": ["-date_created"]
    }

