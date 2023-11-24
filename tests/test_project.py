import pytest

# from app import app
from app.controllers.utils import parse_column_name


def test_utils():
    # res = app.controllers.utils.parse_column_name("Hello")
    # print(res)
    assert parse_column_name("col_m_test") == "test"


# def test_routes():
#     with app.test_client() as test_client:
#         response = test_client.get("/documents")
#         assert "hello" == "hello"
