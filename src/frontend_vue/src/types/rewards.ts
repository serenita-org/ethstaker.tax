export interface RewardsRequest {
    validator_indexes: number[]
    start_date: string
    end_date: string
    expected_fee_recipient_addresses: string[]
}

export interface RewardForDate {
    date: string
    amount_wei: bigint
}

export interface RocketPoolNodeRewardForDate extends RewardForDate {
    node_address: string
    amount_rpl: bigint
}

export interface ValidatorRewardsBase {
    validator_index: number

    consensus_layer_rewards: RewardForDate[] | null
    execution_layer_rewards: RewardForDate[]

    withdrawals: RewardForDate[]
}

export interface ValidatorRewards extends ValidatorRewardsBase{
    consensus_layer_rewards: RewardForDate[]
}

export interface RocketPoolValidatorRewards extends ValidatorRewardsBase {
    consensus_layer_rewards: null
}

export interface RewardsResponseRocketPool {
    validator_rewards_list: RocketPoolValidatorRewards[]
    rocket_pool_node_rewards: RocketPoolNodeRewardForDate[]
}
export interface RewardsResponseFull {
    validator_rewards_list: ValidatorRewards[]
}

export interface PriceForDate {
    date: string
    price: number
}

export interface PricesResponse {
    currency: string
    prices: PriceForDate[]
}

export interface PricesRequestParams {
    start_date: string
    end_date: string
    currency: string
}

type InvalidApiRequestErrorMessage = {
    loc: string[]
    msg: string
    type: string
}

export type InvalidApiRequestResponse = {
    detail: InvalidApiRequestErrorMessage[]
}
