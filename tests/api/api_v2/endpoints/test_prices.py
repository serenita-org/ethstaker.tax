import pytest

from fastapi.testclient import TestClient

from api.app import app


@pytest.mark.usefixtures("_populated_db")
def test_prices():
    with TestClient(app) as client:
        response = client.get(
            "api/v2/prices/ethereum",
            params={
                "start_date": "2023-04-12",
                "end_date": "2023-04-17",
                "currency": "USD",
            }
        )
        data = response.json()

        assert data["currency"] == "USD"
        assert data["prices"] == [{'date': '2023-04-12', 'price': 1920.22}, {'date': '2023-04-13', 'price': 2012.79}, {'date': '2023-04-14', 'price': 2102.95}, {'date': '2023-04-15', 'price': 2093.17}, {'date': '2023-04-16', 'price': 2118.6}, {'date': '2023-04-17', 'price': 2077.54}]
