import {
    RewardForDate,
    RocketPoolBondForDate,
    RocketPoolFeeForDate,
    RocketPoolValidatorRewards,
    ValidatorRewards
} from "../types/rewards.ts";
import {WeiToEthMultiplier} from "../constants.ts";


export function getBondForDate(bonds: RocketPoolBondForDate[], date: string): bigint {
    return bonds[0].bond_value_wei;
}
export function getFeeForDate(fees: RocketPoolFeeForDate[], date: string): bigint {
    return fees[0].fee_value_wei;
}

export function getOperatorReward(validatorRewardsData: RocketPoolValidatorRewards, reward: RewardForDate): bigint {
    const operatorBond = getBondForDate(validatorRewardsData.bonds, reward.date);
    let operatorReward = (reward.amount_wei * operatorBond) / (BigInt(32) * WeiToEthMultiplier);

    const operatorFee = getFeeForDate(validatorRewardsData.fees, reward.date);
    operatorReward += (reward.amount_wei - operatorReward) * operatorFee / WeiToEthMultiplier;
    return operatorReward;
}

export function isRocketPoolValidatorRewards(validatorRewards: ValidatorRewards | RocketPoolValidatorRewards) {
    return "fees" in validatorRewards;
}
