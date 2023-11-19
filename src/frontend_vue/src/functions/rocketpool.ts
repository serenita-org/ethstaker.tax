import {
    RewardForDate,
    RocketPoolBondForDate,
    RocketPoolFeeForDate,
    RocketPoolValidatorRewards,
    ValidatorRewards
} from "../types/rewards.ts";
import {WeiToEthMultiplier} from "../constants.ts";


export function getBondForDate(bonds: RocketPoolBondForDate[], date: Date): bigint {
    if (!date) throw "No date";
    if (bonds.length == 0) {
        return bonds[0].bond_value_wei;
    }
    // Go from most recent date to oldest
    for (const bondForDate of bonds.sort((a, b) => new Date(b.date).valueOf()  - new Date(a.date).valueOf())) {
        if (date > new Date(bondForDate.date)) {
            return bondForDate.bond_value_wei;
        }
    }
    throw `Unable to get bond for date ${date} - ${JSON.stringify(bonds)}`;
}
export function getFeeForDate(fees: RocketPoolFeeForDate[], date: Date): bigint {
    if (!date) throw "No date";
    if (fees.length == 0) {
        return fees[0].fee_value_wei;
    }
    // Go from most recent date to oldest
    for (const feeForDate of fees.sort((a, b) => new Date(b.date).valueOf()  - new Date(a.date).valueOf())) {
        if (date > new Date(feeForDate.date)) {
            return feeForDate.fee_value_wei;
        }
    }
    throw `Unable to get fee for date ${date} - ${JSON.stringify(fees)}`;
}

export function getOperatorReward(bonds: RocketPoolBondForDate[], fees: RocketPoolFeeForDate[], reward: RewardForDate): RewardForDate {
    const rewardDate = new Date(reward.date);

    const operatorBond = getBondForDate(bonds, rewardDate);
    let operatorReward = (reward.amount_wei * operatorBond) / (BigInt(32) * WeiToEthMultiplier);

    const operatorFee = getFeeForDate(fees, rewardDate);
    operatorReward += (reward.amount_wei - operatorReward) * operatorFee / WeiToEthMultiplier;
    return {
        amount_wei: operatorReward, date: reward.date
    };
}

export function isRocketPoolValidatorRewards(validatorRewards: ValidatorRewards | RocketPoolValidatorRewards) {
    return "fees" in validatorRewards;
}
