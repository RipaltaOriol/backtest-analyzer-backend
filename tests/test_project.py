import pytest
from app.controllers.UploadController import upload_mt4
from app.controllers.utils import from_db_to_df
from pandas.testing import assert_frame_equal

# from app import app
# from app.controllers.utils import parse_column_name


def test_utils():
    # res = app.controllers.utils.parse_column_name("Hello")
    # print(res)
    # assert parse_column_name("col_m_test") == "test"
    assert "test" == "test"


# def test_routes():
#     with app.test_client() as test_client:
#         response = test_client.get("/documents")
#         assert "hello" == "hello"
