import logging
import os

import requests


class MetaTraderService:
    def __init__(self) -> None:
        self.mt4_url = os.getenv("MT4_URL")
        self.mt5_url = os.getenv("MT5_URL")

    def discover_server_ip(self, server_name: str, mt_version: str) -> dict:
        mt_url = self.mt4_url if mt_version == "MT4_API" else self.mt5_url
        try:
            payload = {"company": server_name}
            response = requests.get(f"{mt_url}/search", params=payload)
            response.raise_for_status()

            results = response.json()[0].get("results")
            company_server = next(
                (obj for obj in results if obj.get("name") == server_name), None
            )
            if company_server:
                return {"success": True, "server_ips": company_server.get("access")}
            return {"success": False, "message": "Server not found."}
        except requests.RequestException as e:
            logging.error(f"Error discovering server IP for {server_name}: {e}")
            return {
                "success": False,
                "message": "Something went wrong. Please check that account credentials are correct.",
            }

    def connect_account(
        self, account: int, password: str, ip: str, mt_version: str, port: int = 443
    ) -> str:
        mt_url = self.mt4_url if mt_version == "MT4_API" else self.mt5_url
        # Split IP and port if necessary
        try:
            ip, port = ip.split(":")
        except ValueError:
            ip, port = ip, port
        try:
            payload = {"user": account, "password": password, "host": ip, "port": port}
            response = requests.get(f"{mt_url}/connect", params=payload)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"Error connectiong to MT account: {e}")
            return {
                "success": False,
                "message": "Something went wrong. Please check that account credentials are correct.",
            }

    def get_account_history(self, connection_string: str, mt_version: str) -> dict:
        print(connection_string)
        mt_url = self.mt4_url if mt_version == "MT4_API" else self.mt5_url
        try:
            payload = {"id": connection_string}
            response = requests.get(f"{mt_url}/orderhistory", params=payload)
            response.raise_for_status()
            return {"success": True, "account_history": response.json()}
        except requests.RequestException as e:
            logging.error(f"Error fetching account history: {e}")
            return {
                "success": False,
                "message": "Something went wrong. Please check that account credentials are correct.",
            }
