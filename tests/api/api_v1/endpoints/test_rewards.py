import pytest

from fastapi.testclient import TestClient

from api.app import app


@pytest.mark.usefixtures("_populated_db")
def test_rewards():
    with TestClient(app) as client:
        response = client.get(
            "api/v1/rewards",
            params={
                "validator_indexes": [123, ],
                "start_date": "2023-04-12",
                "end_date": "2023-04-17",
                "timezone": "UTC",
                "currency": "USD",

            }
        )
        data = response.json()

        assert round(data["eth_prices"]["2023-04-12"], 3) == 1920.223

        rewards = data["validator_rewards"]
        assert len(rewards) == 1
        for reward_data in rewards:
            assert reward_data["validator_index"] == 123
            assert reward_data["initial_balance"]["balance"] == 34.247005602
            assert reward_data["initial_balance"]["slot"] == 6202798
            assert reward_data["initial_balance"]["date"] == "2023-04-11"
            assert len(reward_data["eod_balances"]) == 6
            assert len(reward_data["exec_layer_block_rewards"]) == 2
            assert len(reward_data["withdrawals"]) == 2
            assert reward_data["withdrawals"][0]["date"] == "2023-04-13"
            assert reward_data["withdrawals"][0]["amount"] == 2.250393207
            assert reward_data["withdrawals"][1]["date"] == "2023-04-16"
            assert reward_data["withdrawals"][1]["amount"] == 0.010466575
            assert reward_data["total_consensus_layer_eth"] == 0.016646477
            assert reward_data["total_consensus_layer_currency"] == 34.198862900922244
            assert reward_data["total_execution_layer_eth"] == 42.032569823218
            assert reward_data["total_execution_layer_currency"] == 89049.39850462688
