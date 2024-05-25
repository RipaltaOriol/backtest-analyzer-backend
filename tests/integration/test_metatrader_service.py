import pytest
from app.services.metatrader_service import MetaTraderService


@pytest.mark.parametrize(
    "server_name, mt_version, account, password",
    [
        ("ICMarketsSC-Demo02", "MT4_API", "21709994", "lgwd26"),
        ("BlueberryMarkets-Demo", "MT5_API", "100007187", "@lBhOn8p"),
    ],
)
def test_metatrader_service_connection(server_name, mt_version, account, password):
    service = MetaTraderService()
    response = service.discover_server_ip(server_name, mt_version)
    assert (
        response["success"] is True
    ), f"Failed to discover server IPs for {server_name} with {mt_version}"
    assert (
        "server_ips" in response and len(response["server_ips"]) > 0
    ), "No IPs returned"

    successful_connection = False
    for ip in response.get("server_ips", []):
        try:
            connection_string = service.connect_account(
                int(account), password, ip, mt_version
            )
            account_history = service.get_account_history(connection_string, mt_version)
            if account_history.get("success"):
                successful_connection = True
                break
        except Exception as e:
            continue

    assert (
        successful_connection is True
    ), f"Failed to establish connnection for {server_name} with {mt_version}"
