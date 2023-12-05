export interface RewardsRequest {
    validator_indexes: number[]
    start_date: string
    end_date: string
}

export interface RewardForDate {
    date: string
    amount_wei: bigint
}

export interface RocketPoolNodeRewardForDate extends RewardForDate {
    node_address: string
    amount_rpl: bigint
}

export interface ValidatorRewards {
    validator_index: number

    consensus_layer_rewards: RewardForDate[]
    execution_layer_rewards: RewardForDate[]

    withdrawals: RewardForDate[]
}

export interface RocketPoolBondForDate {
    date: string
    bond_value_wei: bigint
}
export interface RocketPoolFeeForDate {
    date: string
    fee_value_wei: bigint
}

export interface RocketPoolValidatorRewards extends ValidatorRewards {
    bonds: RocketPoolBondForDate[]
    fees: RocketPoolFeeForDate[]
}

export interface RewardsResponse {
    validator_rewards: ValidatorRewards[] | RocketPoolValidatorRewards[]
    rocket_pool_node_rewards: RocketPoolNodeRewardForDate[]
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
