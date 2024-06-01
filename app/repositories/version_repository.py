import json
from io import StringIO

import pandas as pd
from app.models.Setup import Setup
from app.serializers.index import json_serial


class VersionRepository:
    @staticmethod
    def get_version_by_id(id: str) -> Setup:
        return Setup.objects(id=id).get()

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
    def update_version_by_id(**kwargs) -> None:
        id = kwargs.pop("id", None)
        if id:
            Setup.objects(id=id).update(**kwargs)

    @staticmethod
    def get_versions_by_account(account_id):
        return Setup.objects(documentId=account_id)

    @staticmethod
    def remove_version_filter(version, filter) -> None:
        version.modify(pull__filters=filter.pk)

    @staticmethod
    def update_version_state(version, data, fields) -> None:
        version.modify(__raw__={"$set": {"state": {"fields": fields, "data": data}}})

    # TODO: review this method and test also this method should be in a service
    """
    Proposed code for ChatGBP
    try:
        df = pd.DataFrame(version.state, orient="index")
        df[date_column] = pd.to_datetime(df[date_column]) + pd.Timedelta(minutes=-timezone_offset)
        df.set_index(date_column, inplace=True)
        return df, None
    except Exception as e:
            return None, str(e)
    """

    @staticmethod
    def get_version_dataframe(version, orient: str = "index"):
        data = version.state.get("data", {})
        parsed_state = json.dumps(data, default=json_serial)

        # get columns that have to be parsed to datetime
        date_columns = [
            column_name
            for column_name, dtype in version.state.get("fields", {}).items()
            if dtype.startswith("datetime64")
        ]
        # I personally do not like having StringIO because I don't understand why is it necessary
        # although it doesn't work without it. Root problem from imgs being [] in json.
        return pd.read_json(
            StringIO(parsed_state), orient=orient, convert_dates=date_columns
        )

    @staticmethod
    def get_version_columns(version):
        return version.state.get("fields", {}).keys()
