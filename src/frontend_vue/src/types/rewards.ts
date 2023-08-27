export interface RewardsRequest {
    validator_indexes: number[]
    start_date: string
    end_date: string
}

export interface RewardForDate {
    date: string
    amount_wei: bigint
}

export interface ValidatorRewards {
    validator_index: number

    consensus_layer_rewards: RewardForDate[]
    execution_layer_rewards: RewardForDate[]

    withdrawals: RewardForDate[]
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
