from datetime import datetime
from enum import Enum

from app.models.Template import Template
from app.models.User import User
from mongoengine.document import DynamicDocument, EmbeddedDocument
from mongoengine.fields import (
    DateTimeField,
    DictField,
    EmbeddedDocumentField,
    EnumField,
    FloatField,
    ListField,
    ReferenceField,
    StringField,
)


class TradeCondition(EmbeddedDocument):
    column = StringField(required=True)
    condition = StringField(required=True)
    value = StringField(default=None)


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    AUD = "AUD"
    NZD = "NZD"
    CHF = "CHF"
    JPY = "JPY"
    CAD = "CAD"


# TODO: set default balance to all account
class Document(DynamicDocument):
    name = StringField()
    author = ReferenceField(User)
    template = ReferenceField(Template)
    template_mapping = DictField()
    state = DictField()
    balance = FloatField(default=0.0, min=0.0)
    account_currency = EnumField(Currency, defaul=Currency.USD)
    open_conditions = ListField(EmbeddedDocumentField(TradeCondition))
    # TODO: transform this into an Enum
    source = StringField()
    metaapi_id = StringField()
    meta_account = StringField()
    meta_password = StringField()
    meta_server = StringField()
    date_created = DateTimeField(default=datetime.utcnow)

    def with_children(self):
        document = {
            "id": str(self.id),
            "name": self.name,
            "source": self.source,
            "date": self.date_created,
            "template": {"name": self.template.name, "id": str(self.template.id)}
            if self.template
            else None,
        }

        return document

    meta = {
        "collection": "documents",
        "indexes": ["name"],
        "ordering": ["-date_created"],
    }
