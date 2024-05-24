from app.models.User import User
from app.serializers.index import json_serial


class UserRepository:
    @staticmethod
    def get_user_by_id(id: str) -> User:
        return User.objects(id=id).get()
