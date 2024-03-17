import requests

# TODO: change URL and add to .env
MT4_URL = "https://tradesharpener-001-site1.ftempurl.com"


def discover_server_ip(server_name: str) -> object:
    try:
        payload = {"company": server_name}
        response = requests.get(f"{MT4_URL}/search", params=payload).json()

        # TODO: maybe do some more checks
        # TODO: reuslt can be within another comany
        companies = response[0].get("results")

        company_server = next(
            (obj for obj in companies if obj.get("name") == server_name), None
        )
        print("Found", company_server)
        if company_server:
            return {"success": True, "server_ips": company_server.get("access")}
        else:
            return {"success": True, "message": "Server not found."}
    except Exception as err:
        print(err)


def connect_account(account: int, password: str, ip: str, port: int = 443) -> str:
    # TODO: HANDLE WRONG RESPONSE
    payload = {"user": account, "password": password, "host": ip, "port": port}
    response = requests.get(f"{MT4_URL}/connect", params=payload)
    connection_string = response.text
    return connection_string


def get_account_history(connection_string: str) -> object:
    try:
        payload = {"id": connection_string}
        response = requests.get(f"{MT4_URL}/orderhistory", params=payload).json()
        return {"success": True, "account_history": response}
    except Exception as err:
        print(err)
        return {"success": False}
