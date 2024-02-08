export interface BalanceAtSlot {
    date: string;
    slot: number;
    balance: number;
}
export interface EndOfDayBalance extends BalanceAtSlot {}
export interface InitialBalance extends BalanceAtSlot {}

export interface ExecLayerBlockReward {
    date: string;
    reward: number;
}


export interface Withdrawal {
    date: string;
    amount: number;
}


export interface ValidatorRewards {
    validator_index: number;
    initial_balance: InitialBalance;
    eod_balances: EndOfDayBalance[];
    exec_layer_block_rewards: ExecLayerBlockReward[];
    withdrawals: Withdrawal[];
    total_consensus_layer_eth: number;
    total_consensus_layer_currency: number;
    total_execution_layer_eth: number;
    total_execution_layer_currency: number;
}

export interface AggregateRewards {
    validator_rewards: ValidatorRewards[];
    currency: string;
    eth_prices: Record<string, number>;
}
