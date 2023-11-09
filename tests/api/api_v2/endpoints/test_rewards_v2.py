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

        for validator_data in data["validator_rewards"]:
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


@pytest.mark.usefixtures("_populated_db")
def test_rewards_rocket_pool():
    with TestClient(app) as client:
        response = client.post(
            "api/v2/rewards",
            json={
                "validator_indexes": [461308, 584908],
                "start_date": "2023-04-12",
                "end_date": "2023-04-17",
            }
        )
        data = response.json()

        # 2 minipools from the same Rocketpool node => 2 validator rewards, but only 1 Rocket Pool (node) reward
        assert len(data["validator_rewards"]) == 2

        assert all("bonds" in vr for vr in data["validator_rewards"])
        assert all("fees" in vr for vr in data["validator_rewards"])

        assert len(data["rocket_pool_node_rewards"]) == 1

        minipool_16eth_bond_reduced_rewards = data["validator_rewards"][0]

        # Bond reduction event
        assert len(minipool_16eth_bond_reduced_rewards["bonds"]) == 2
        assert len(minipool_16eth_bond_reduced_rewards["fees"]) == 2

        minipool_leb8_rewards = data["validator_rewards"][1]

        # No bond reduction event
        assert len(minipool_leb8_rewards["bonds"]) == 1
        assert len(minipool_leb8_rewards["fees"]) == 1

        rocket_pool_node_rewards_datapoint = data["rocket_pool_node_rewards"][0]
        assert rocket_pool_node_rewards_datapoint["date"] == "2023-04-13"
        assert rocket_pool_node_rewards_datapoint["node_address"] == "0x5a8b39df6f1231b5d68036c090a2c5d126eb72d2"
        assert rocket_pool_node_rewards_datapoint["amount_wei"] == 34078389543558842
        assert rocket_pool_node_rewards_datapoint["amount_rpl"] == 8660175360427081131
