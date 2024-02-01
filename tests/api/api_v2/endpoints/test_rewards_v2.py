import datetime
from decimal import Decimal

import pytest
import pytz

from fastapi.testclient import TestClient
from api.api_v2.endpoints.rewards import get_rocket_pool_reward_share_withdrawal, get_rocket_pool_reward_share_proposal_fee_distributor

from api.app import app
from db.tables import Withdrawal, RocketPoolBondReduction, RocketPoolMinipool
from providers.beacon_node import BeaconNode
from providers.execution_node import ExecutionNode
from providers.rocket_pool import RocketPoolDataProvider


@pytest.mark.parametrize(
    ["withdrawal_amount_gwei", "slot", "expected_node_share"],
    [
        pytest.param(
            Decimal(10_000_000),
            100,
            5_900_000_000_000_000,
            id="Partial withdrawal before bond reduction, initial fee & bond should be used"
        ),
        pytest.param(
            32 * Decimal(1e9) + Decimal(50_000_000),
            5_074_010,
            29_500_000_000_000_000,
            id="Full withdrawal before bond reduction, initial fee & bond should be used"
        ),
        pytest.param(
            Decimal(10_000_000),
            BeaconNode.slot_for_datetime(dt=datetime.datetime(year=2023, month=5, day=1, tzinfo=pytz.UTC)) + 1_000,
            3_550_000_000_000_000,
            id="Partial withdrawal after 1st bond reduction, LEB8"
        ),
        pytest.param(
            Decimal(10_000_000),
            BeaconNode.slot_for_datetime(dt=datetime.datetime(year=2025, month=1, day=1, tzinfo=pytz.UTC)) + 1_000,
            2300000000000000,
            id="Partial withdrawal after 2nd bond reduction, LEB4"
        ),
    ]
)
@pytest.mark.asyncio
async def test_get_rocket_pool_reward_share_withdrawal(withdrawal_amount_gwei, slot, expected_node_share):
    # Set up - a validator with 2 bond reductions
    initial_bond = Decimal(16_000_000_000_000_000_000)
    initial_fee = Decimal(180_000_000_000_000_000)
    bond_reductions = [
        # Bond reduction 1 - to 8ETH, network fee 14%
        RocketPoolBondReduction(
            timestamp=datetime.datetime(year=2023, month=5, day=1, tzinfo=pytz.UTC),
            new_bond_amount=Decimal(8_000_000_000_000_000_000),
            new_fee=Decimal(140_000_000_000_000_000)
        ),
        # Bond reduction 1 - to 4ETH, network fee 12%
        RocketPoolBondReduction(
            timestamp=datetime.datetime(year=2025, month=1, day=1, tzinfo=pytz.UTC),
            new_bond_amount=Decimal(4_000_000_000_000_000_000),
            new_fee=Decimal(120_000_000_000_000_000)
        ),
    ]

    minipool = RocketPoolMinipool(
        minipool_address="0xb8d17ec656d5353d04d7f876e0ff6cc10f9d3b65",
        bond_reductions=bond_reductions,
        initial_bond_value=initial_bond,
        initial_fee_value=initial_fee,
    )

    share = await get_rocket_pool_reward_share_withdrawal(
        withdrawal=Withdrawal(
            slot=slot,
            validator_index=123,
            amount_gwei=withdrawal_amount_gwei,
        ),
        minipool=minipool
    )
    assert share.amount_wei == expected_node_share


@pytest.mark.asyncio
async def test_get_rocket_pool_reward_share_proposal_fee_distributor():
    # Easiest case - fee distributor delegate supports getNodeShare()
    # at time of block proposal
    share = await get_rocket_pool_reward_share_proposal_fee_distributor(
        node_address="0xb81e87018ec50d17116310c87b36622807581fa6",
        fee_distributor="0xd03979c6952f74e80fe0c8a126c32fc1454b1627",
        slot=8_211_441,
        beacon_node=BeaconNode(),
        rocket_pool_data=RocketPoolDataProvider(execution_node=ExecutionNode()),
    )
    # Full reward in wei - 25_468_585_834_907_426
    # It was proposed by an LEB8 @ 14%
    assert share == 9_041_347_971_392_136

    # Manual calculation - fee distributor does not support getNodeShare()
    # at time of block proposal (before Redstone upgrade)
    share = await get_rocket_pool_reward_share_proposal_fee_distributor(
        node_address="0xb81e87018ec50d17116310c87b36622807581fa6",
        fee_distributor="0xd03979c6952f74e80fe0c8a126c32fc1454b1627",
        slot=6_086_164,
        beacon_node=BeaconNode(),
        rocket_pool_data=RocketPoolDataProvider(execution_node=ExecutionNode()),
    )
    # Full reward in wei - 28_388_055_379_583_825
    # It was proposed by an LEB16 @ 15%
    assert share == 16_323_131_843_260_699


@pytest.mark.usefixtures("_populated_db")
def test_rewards():
    with TestClient(app) as client:
        response = client.post(
            "api/v2/rewards/full",
            json={
                "validator_indexes": [123, 124],
                "start_date": "2023-04-12",
                "end_date": "2023-04-17",
            }
        )
        data = response.json()

        for validator_data in data["validator_rewards_list"]:
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
            "api/v2/rewards/rocket_pool",
            json={
                "validator_indexes": [461308, 584908],
                "start_date": "2023-04-12",
                "end_date": "2023-04-17",
            }
        )
        assert response.status_code == 200
        data = response.json()

        # 2 minipools from the same Rocketpool node => 2 validator rewards, but only 1 Rocket Pool (node) reward
        assert len(data["validator_rewards_list"]) == 2
        assert len(data["rocket_pool_node_rewards"]) == 1

        # TODO add some withdrawals to conftest and check returned "NO share" values here
        minipool_16eth_bond_reduced_rewards = data["validator_rewards_list"][0]
        minipool_leb8_rewards = data["validator_rewards_list"][1]

        rocket_pool_node_rewards_datapoint = data["rocket_pool_node_rewards"][0]
        assert rocket_pool_node_rewards_datapoint["date"] == "2023-04-13"
        assert rocket_pool_node_rewards_datapoint["node_address"] == "0x5a8b39df6f1231b5d68036c090a2c5d126eb72d2"
        assert rocket_pool_node_rewards_datapoint["amount_wei"] == 34078389543558842
        assert rocket_pool_node_rewards_datapoint["amount_rpl"] == 8660175360427081131
