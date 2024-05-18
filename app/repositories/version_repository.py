from app.models.Setup import Setup


class VersionRepository:
    @staticmethod
    def create_version(name, author, account, default: False, state) -> None:
        Setup(
            name=name,
            author=author,
            documentId=account,
            default=default,
            state=state,
        ).save()

    @staticmethod
    def get_versions_by_account(account_id):
        return Setup.objects(documentId=account_id)

    @staticmethod
    def remove_version_filter(version, filter) -> None:
        version.modify(pull__filters=filter.pk)

    @staticmethod
    def update_version_state(version, data, fields) -> None:
        version.modify(__raw__={"$set": {"state": {"fields": fields, "data": data}}})
