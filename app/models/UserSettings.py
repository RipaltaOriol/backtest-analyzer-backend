import json
from datetime import datetime
from app.models.User import User
from app.models.Template import Template
from bson.json_util import default, dumps
from mongoengine.document import DynamicDocument

from mongoengine.fields import (
    ListField,
    ReferenceField,
)


class UserSettings(DynamicDocument):
    user = ReferenceField(User)
    templates = ListField(ReferenceField(Template))

    def get_templates(self):
        templates = []
        for template in self.templates:
            templates.append(
                {
                    "id": str(template.id),
                    "name": template.name,
                    "description": template.description,
                }
            )

        return json.loads(dumps(templates))

    meta = {"collection": "usersettings"}
