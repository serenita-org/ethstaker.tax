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
                slot=6_202_798,  # Apr-11-2023 23:59:59 UTC
                validator_index=226152,
                balance=34.247005602,
            ),
            Balance(
                slot=6_209_998,  # Apr-12-2023 23:59:59 UTC
                validator_index=226152,
                balance=34.249813825,
            ),
            Balance(
                slot=6_217_198,  # Apr-13-2023 23:59:59 UTC
                validator_index=226152,
                balance=32.002092287,
            ),
            Balance(
                slot=6_224_398,  # Apr-14-2023 23:59:59 UTC
                validator_index=226152,
                balance=32.004865082,
            ),
            Balance(
                slot=6_231_598,  # Apr-15-2023 23:59:59 UTC
                validator_index=226152,
                balance=32.00765765,
            ),
            Balance(
                slot=6_238_798,  # Apr-16-2023 23:59:59 UTC
                validator_index=226152,
                balance=32.00001272,
            ),
            Balance(
                slot=6_245_998,  # Apr-17-2023 23:59:59 UTC
                validator_index=226152,
                balance=32.002792297,
            ),
            Withdrawal(
                slot=6_211_586,  # Apr-13-2023 05:17:35 UTC
                validator_index=226152,
                amount_gwei=2_250_393_207,
            ),
            Withdrawal(
                slot=6_238_774,  # Apr-16-2023 23:55:11 UTC
                validator_index=226152,
                amount_gwei=10_466_575,
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
            assert reward_data["initial_balance"]["slot"] == 6202798
            assert reward_data["initial_balance"]["date"] == "2023-04-11"
            assert len(reward_data["eod_balances"]) == 6
            assert len(reward_data["exec_layer_block_rewards"]) == 0
            assert len(reward_data["withdrawals"]) == 2
            assert reward_data["withdrawals"][0]["date"] == "2023-04-13"
            assert reward_data["withdrawals"][0]["amount"] == 2.250393207
            assert reward_data["withdrawals"][1]["date"] == "2023-04-16"
            assert reward_data["withdrawals"][1]["amount"] == 0.010466575
            assert reward_data["total_consensus_layer_eth"] == 0.016646476999997738
            assert reward_data["total_consensus_layer_currency"] == 34.198862900917845
