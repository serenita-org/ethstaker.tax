import datetime
import random

import pytest
import pytz

from db.db_helpers import session_scope
from db.tables import Balance, Withdrawal, BlockReward
from providers.beacon_node import BeaconNode


@pytest.fixture(scope="session")
def _populated_db():
    with session_scope() as session:
        for db_entry in [
            Balance(
                slot=6_202_798,  # Apr-11-2023 23:59:59 UTC
                validator_index=123,
                balance=34.247005602,
            ),
            Balance(
                slot=6_202_798,  # Apr-11-2023 23:59:59 UTC
                validator_index=124,
                balance=32.25,
            ),
            Balance(
                slot=6_209_998,  # Apr-12-2023 23:59:59 UTC
                validator_index=123,
                balance=34.249813825,
            ),
            Balance(
                slot=6_209_998,  # Apr-12-2023 23:59:59 UTC
                validator_index=124,
                balance=32.26,
            ),
            Balance(
                slot=6_217_198,  # Apr-13-2023 23:59:59 UTC
                validator_index=123,
                balance=32.002092287,
            ),
            Balance(
                slot=6_217_198,  # Apr-13-2023 23:59:59 UTC
                validator_index=124,
                balance=32.27,
            ),
            Balance(
                slot=6_224_398,  # Apr-14-2023 23:59:59 UTC
                validator_index=123,
                balance=32.004865082,
            ),
            Balance(
                slot=6_224_398,  # Apr-14-2023 23:59:59 UTC
                validator_index=124,
                balance=32.28,
            ),
            Balance(
                slot=6_231_598,  # Apr-15-2023 23:59:59 UTC
                validator_index=123,
                balance=32.00765765,
            ),
            Balance(
                slot=6_231_598,  # Apr-15-2023 23:59:59 UTC
                validator_index=124,
                balance=32.29,
            ),
            Balance(
                slot=6_238_798,  # Apr-16-2023 23:59:59 UTC
                validator_index=123,
                balance=32.00001272,
            ),
            Balance(
                slot=6_238_798,  # Apr-16-2023 23:59:59 UTC
                validator_index=124,
                balance=32.3,
            ),
            Balance(
                slot=6_245_998,  # Apr-17-2023 23:59:59 UTC
                validator_index=123,
                balance=32.002792297,
            ),
            Balance(
                slot=6_245_998,  # Apr-17-2023 23:59:59 UTC
                validator_index=124,
                balance=32.31,
            ),
            Withdrawal(
                slot=6_211_586,  # Apr-13-2023 05:17:35 UTC
                validator_index=123,
                amount_gwei=2_250_393_207,
            ),
            Withdrawal(
                slot=6_238_774,  # Apr-16-2023 23:55:11 UTC
                validator_index=123,
                amount_gwei=10_466_575,
            ),
            BlockReward(
                slot=6_226_574,  # Apr-15-2023 07:15:11 UTC
                proposer_index=123,
                fee_recipient="0xdeadbeef",
                priority_fees_wei=29608930218000001,
                block_extra_data=None,
                mev=False,
                mev_reward_recipient=None,
                mev_reward_value_wei=None,
            ),
            BlockReward(
                slot=6_238_574,  # Apr-16-2023 23:15:11 UTC
                proposer_index=123,
                fee_recipient="0xdeadbeef",
                priority_fees_wei=29608930218000001,
                block_extra_data=None,
                mev=True,
                mev_reward_recipient="0xdeadbeef",
                mev_reward_value_wei=42002960893000000000,
            ),
            BlockReward(
                slot=6_238_570,  # Apr-16-2023 23:14:23 UTC
                proposer_index=124,
                fee_recipient="0xdeadbeef",
                priority_fees_wei=29608930218000001,
                block_extra_data=None,
                mev=True,
                mev_reward_recipient="0xdeadbeef",
                mev_reward_value_wei=42002960893000000000,
            ),
            *[
                BlockReward(
                    slot=slot,
                    proposer_index=random.randint(1_000, 1_000_000),
                    fee_recipient=random.choice([None, "0xdeadbeef"]),
                    priority_fees_wei=1e18 / 4,
                    block_extra_data=None,
                    mev=random.choice([True, False]),
                    mev_reward_recipient="0xdeadbeef",
                    mev_reward_value_wei=random.randint(int(1e18 / 100), int(1e19)),
                ) for slot in range(
                    BeaconNode.slot_for_datetime(datetime.datetime.now(tz=pytz.UTC)) - 1_000,
                    BeaconNode.slot_for_datetime(datetime.datetime.now(tz=pytz.UTC))
                )
            ]
        ]:
            session.add(db_entry)
