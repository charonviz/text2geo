"""
Tests for text2geo.

Run with: pytest tests/
"""

import pytest
from unittest.mock import patch, MagicMock
from text2geo.exceptions import InvalidDatasetError, DatasetNotFoundError
from text2geo.data import available_datasets, _validate_dataset


def test_available_datasets():
    ds = available_datasets()
    assert "ru" in ds
    assert "cis" in ds
    assert "world" in ds


def test_invalid_dataset():
    with pytest.raises(InvalidDatasetError):
        _validate_dataset("mars")


def test_dataset_not_found_error_message():
    err = DatasetNotFoundError("cis", "/tmp/data")
    assert "cis" in str(err)
    assert "text2geo.download" in str(err)
