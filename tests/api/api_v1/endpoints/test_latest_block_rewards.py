import pytest
from fastapi.testclient import TestClient

from api.app import app


@pytest.mark.usefixtures("_populated_db")
def test_latest_block_rewards():
    with TestClient(app) as client:
        response = client.get(
            "api/v1/latest_block_rewards",
        )
        data = response.json()

        assert len(data) == 50
