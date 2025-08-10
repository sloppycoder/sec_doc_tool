import logging
import os
from pathlib import Path

import pytest

mock_data_path = Path(__file__).parent / "mockdata/cache"
os.environ["STORAGE_PREFIX"] = str(mock_data_path)

logging.getLogger("urllib3").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def mock_file_content():
    def _mock_file_content(file_name):
        with open(mock_data_path / file_name) as f:
            return f.read()

    return _mock_file_content
