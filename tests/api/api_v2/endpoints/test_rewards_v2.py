import pytest

from fastapi.testclient import TestClient

from api.app import app


@pytest.mark.usefixtures("_populated_db")
def test_rewards():
    with TestClient(app) as client:
        response = client.post(
            "api/v2/rewards",
            json={
                "validator_indexes": [123, 124],
                "start_date": "2023-04-12",
                "end_date": "2023-04-17",
            }
        )
        data = response.json()

        for validator_data in data:
            assert len(validator_data["consensus_layer_rewards"]) == 6

            if validator_data["validator_index"] == 123:
                assert validator_data["consensus_layer_rewards"] == [
                    {'date': '2023-04-12', 'amount_wei': 2808223000000000},
                    {'date': '2023-04-13', 'amount_wei': 2671669000000000},
                    {'date': '2023-04-14', 'amount_wei': 2772795000000000},
                    {'date': '2023-04-15', 'amount_wei': 2792568000000000},
                    {'date': '2023-04-16', 'amount_wei': 2821645000000000},
                    {'date': '2023-04-17', 'amount_wei': 2779577000000000}
                ]
                assert validator_data["execution_layer_rewards"] == [
                    {'amount_wei': 29608930218000001, 'date': '2023-04-15'},
                    {'amount_wei': 42002960893000000000, 'date': '2023-04-16'},
                ]
                assert validator_data["withdrawals"] == [
                    {'date': '2023-04-13', 'amount_wei': 2250393207000000000},
                    {'date': '2023-04-16', 'amount_wei': 10466575000000000},
                ]
            elif validator_data["validator_index"] == 124:
                assert validator_data["consensus_layer_rewards"] == [{'date': '2023-04-12', 'amount_wei': 10000000000000000}, {'date': '2023-04-13', 'amount_wei': 10000000000000000}, {'date': '2023-04-14', 'amount_wei': 10000000000000000}, {'date': '2023-04-15', 'amount_wei': 10000000000000000}, {'date': '2023-04-16', 'amount_wei': 10000000000000000}, {'date': '2023-04-17', 'amount_wei': 10000000000000000}]
                assert validator_data["execution_layer_rewards"] == [{'amount_wei': 42002960893000000000, 'date': '2023-04-16'}]
                assert validator_data["withdrawals"] == []
            else:
                raise ValueError("Unknown validator index")
