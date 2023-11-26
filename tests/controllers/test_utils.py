import os

import pytest
from app.controllers.UploadController import upload_mt4
from app.controllers.utils import from_db_to_df
from pandas.testing import assert_frame_equal
from tests.controllers.utils_data import mt4_file_db


def test_utils():
    # import xlsx file
    file_path = os.path.abspath("tests/data/mt4_to_tradesharpener.xlsx")
    file_db = upload_mt4(file_path)
    file_df = from_db_to_df(file_db).reset_index(drop=True)

    # testing data as db file
    mt4_test_df = from_db_to_df(mt4_file_db).reset_index(drop=True)

    # check both dataframes are equal
    assert_frame_equal(file_df, mt4_test_df)
