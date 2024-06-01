from app.controllers.utils import from_df_to_db
from app.repositories.version_repository import VersionRepository
from app.services.filter_service import FilterService


class VersionService:
    def __init__(self):
        self.version_repository = VersionRepository()
        self.filter_service = FilterService()

    def get_version_note(self, version_id) -> str:
        version = self.version_repository.get_version_by_id(version_id)
        return version.notes if version.notes else ""

    def put_version_note(self, version_id, data) -> str:
        self.version_repository.update_version_by_id(**{"id": version_id, **data})

    def update_version_from_account_without_filters(
        self, account_id, account_data, account_fields, filter_list
    ):

        versions = self.version_repository.get_versions_by_account(account_id)

        for version in versions:
            new_state = account_data
            for filter in version.filters:
                if filter.column not in filter_list:
                    new_state = self.filter_service.apply_filter(new_state, filter)
                else:
                    # remove filter
                    self.version_repository.remove_version_filter(version, filter)
                    filter.delete()

            version_state = from_df_to_db(new_state)
            self.version_repository.update_version_state(
                version, version_state, account_fields
            )
