from datetime import datetime

from app.models.User import User
from app.models.Template import Template

from mongoengine.document import DynamicDocument
from mongoengine.fields import DateTimeField, DictField, ReferenceField, StringField


class Document(DynamicDocument):
    name = StringField()
    author = ReferenceField(User)
    template = ReferenceField(Template)
    state = DictField()
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
