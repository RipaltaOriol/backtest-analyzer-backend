import logging

from app.constants.account_source import ACCOUNT_SOURCE_MAP
from app.controllers.UploadController import upload_meta_api
from app.models.Document import Document
from app.repositories.template_repository import TemplateRepository
from app.repositories.version_repository import VersionRepository
from app.services.metatrader_service import MetaTraderService


class AccountManager:
    def __init__(self, user):
        self.user = user
        self.meta_trade_service = MetaTraderService()
        self.template_repository = TemplateRepository()
        self.version_repository = VersionRepository()

    def fetch_from_metatrader(self, account, password, server, platform) -> dict:
        # Check the account does not exist already
        if Document.objects(name=f"{account}+{server}", author=self.user).count() > 0:
            return {"msg": "This account already exists", "success": False}

        # Find the IP address of the server
        server_ips = self.meta_trade_service.discover_server_ip(server, platform)
        if not server_ips.get("success"):
            logging.error(f"Server IP discovery failed with server: {server}")
            return {"msg": "Server not found. Try again later.", "success": False}

        successful_connection = False
        for ip in server_ips.get("server_ips", []):
            try:
                connection_string = self.meta_trade_service.connect_account(
                    int(account), password, ip, platform
                )
                account_history = self.meta_trade_service.get_account_history(
                    connection_string, platform
                )
                if account_history.get("success"):
                    successful_connection = True
                    break
            except Exception as e:
                logging.error(
                    f"Failed to connect or fetch history from IP {ip}: {str(e)}"
                )
                continue

        if not successful_connection:
            return {
                "msg": "Failed to connect to any server IPs. Try again later.",
                "success": False,
            }

        if account_history.get("success"):
            state = upload_meta_api(account_history.get("account_history"))
            default_template = self.template_repository.get_template()

            account_doc = Document(
                name=f"{account}+{server}",
                author=self.user,
                state=state,
                source=ACCOUNT_SOURCE_MAP.get(platform),
                template=default_template,
                metaapi_id=connection_string,
                meta_account=account,
                meta_password=password,
                meta_server=server,
            )
            account_doc.save()

            self.version_repository.create_version(
                "Default", self.user, account_doc, True, state
            )

            return {"msg": "Account successfully extracted!", "success": True}
        return {
            "msg": "Failed to retrieve account history. Try again later.",
            "success": False,
        }
