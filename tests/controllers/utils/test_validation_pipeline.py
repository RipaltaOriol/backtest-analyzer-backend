import os

import pytest
from app.controllers.utils import validation_pipeline
from tests.controllers.utils.validation_pipeline_data import (
    validation_pipeline_data,
    validation_pipeline_result,
)


def test_validation_pipeline():
    assert validation_pipeline_result == validation_pipeline(validation_pipeline_data)
