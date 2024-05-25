import logging
import os
from typing import Tuple

import numpy as np
import pandas as pd
import requests
from app.constants.columns import get_mt_columns_rename, get_mt_target_columns
from app.controllers.utils import from_df_to_db
from app.controllers.validation_pipelines.upload_pipelines import (
    df_column_datatype_validation,
)
from app.services.columns_service import ColumnsService


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

    def get_accout_history_df(
        self, account_history: dict, mt_version: str
    ) -> Tuple[dict, str]:
        account = (
            account_history.get("orders", {})
            if mt_version == "MT5_API"
            else account_history
        )
        if not account:
            return None, "No data found in the account history"

        df = pd.DataFrame.from_dict(account, orient="columns")
        pd.set_option("display.max_rows", None, "display.max_columns", None)
        order_type = "orderType" if mt_version == "MT5_API" else "type"
        df[["ticket", "symbol", order_type, "swap", "profit"]]
        df = df.loc[
            df[order_type].isin(
                ["Buy", "Sell", "BuyStop", "SellStop", "SellLimit", "BuyLimit"]
            )
        ]

        # Include executed orders
        # df = df.loc[df['type'].isin(['Buy', 'Sell'])]

        # Filter out specific columns
        df = df[get_mt_target_columns(mt_version)]
        df.loc[:, "openTime"] = pd.to_datetime(df["openTime"], utc=True)
        df.loc[:, "closeTime"] = pd.to_datetime(df["closeTime"], utc=True)
        df["col_d"] = np.where(
            df[order_type].str.startswith("Buy"),
            "Long",
            np.where(df[order_type].str.startswith("Sell"), "Short", None),
        )
        df.rename(
            columns=get_mt_columns_rename(mt_version), errors="raise", inplace=True
        )
        df.set_index("#", inplace=True, drop=False)

        # Add all required columns
        columns_service = ColumnsService(df)
        columns_service.add_required_columns()

        # Validate dataframe dtypes
        df = df_column_datatype_validation(df)

        state = {
            "data": from_df_to_db(df, add_index=False),
            "fields": df.dtypes.apply(lambda x: x.name).to_dict(),
        }

        return state, None
