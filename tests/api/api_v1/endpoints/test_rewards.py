import pytest

from fastapi.testclient import TestClient

from api.app import app
from db.db_helpers import session_scope
from db.tables import Balance, Withdrawal


@pytest.fixture
def _populated_db():
    with session_scope() as session:
        for db_entry in [
            Balance(
                slot=6_202_798,
                validator_index=226152,
                balance=34.247005602,
            ),
            Balance(
                slot=6_209_998,
                validator_index=226152,
                balance=34.249813825,
            ),
            Balance(
                slot=6_217_198,
                validator_index=226152,
                balance=32.002092287,
            ),
            Balance(
                slot=6_224_398,
                validator_index=226152,
                balance=32.004865082,
            ),
            Balance(
                slot=6_231_598,
                validator_index=226152,
                balance=32.00765765,
            ),
            Balance(
                slot=6_238_798,
                validator_index=226152,
                balance=32.00001272,
            ),
            Withdrawal(
                slot=6211586,
                validator_index=226152,
                amount=2250393207,
            ),
            Withdrawal(
                slot=6238774,
                validator_index=226152,
                amount=10466575,
            ),
        ]:
            session.add(db_entry)


@pytest.mark.usefixtures("_populated_db")
def test_rewards():
    from indexer.block_rewards.main import reset_missing_data_cache
    reset_missing_data_cache()

    with TestClient(app) as client:
        response = client.get(
            "api/v1/rewards",
            params={
                "validator_indexes": [226152, ],
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
            assert reward_data["validator_index"] == 226152
            assert reward_data["initial_balance"]["balance"] == 34.247005602
            assert len(reward_data["eod_balances"]) == 6
            assert len(reward_data["exec_layer_block_rewards"]) == 0
            assert len(reward_data["withdrawals"]) == 2
            assert reward_data["withdrawals"][0]["date"] == "2023-04-13"
            assert reward_data["withdrawals"][0]["amount"] == 2.250393207e-09
            assert reward_data["total_consensus_layer_eth"] == 0.01572061699999535
            assert reward_data["total_consensus_layer_currency"] == 32.263073623277684
