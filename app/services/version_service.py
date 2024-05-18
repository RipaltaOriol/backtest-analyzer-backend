from app.controllers.utils import from_df_to_db


class VersionService:
    def __init__(self, version_repsitory, filter_service):
        self.version_repository = version_repsitory
        self.filter_service = filter_service

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
