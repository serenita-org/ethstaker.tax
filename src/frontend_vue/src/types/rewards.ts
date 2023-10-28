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

export interface RocketPoolValidatorRewards extends ValidatorRewards {
    fee: bigint
    bond_reduced: boolean
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
