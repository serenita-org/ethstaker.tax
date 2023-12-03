import {
    PriceForDate,
    PricesResponse,
    RewardForDate, RocketPoolNodeRewardForDate,
    RocketPoolValidatorRewards,
    ValidatorRewards
} from "../../types/rewards.ts";
import { gweiToEthMultiplier, WeiToGweiMultiplier } from "../../constants.ts";
import {getOperatorReward, isRocketPoolValidatorRewards} from "../../functions/rocketpool.ts";

const SEPARATOR = ";";


function createLinkAndDownload(csvContent: string): void {
    // Create a Blob with the CSV content
    const blob = new Blob([csvContent], { type: "text/csv" });

    // Create a URL for the Blob
    const csvURL = URL.createObjectURL(blob);

    // Create a download link
    const link = document.createElement("a");
    link.href = csvURL;
    link.download = "rewards_data.csv"; // Set the desired file name
    link.innerText = "Download CSV";

    // "Click" the link to download the file
    link.click();
}

export function downloadAsCsv(
    validatorRewardsData: (ValidatorRewards|RocketPoolValidatorRewards)[],
    rocketPoolNodeRewards: RocketPoolNodeRewardForDate[],
    useConsensusIncomeOnWithdrawal: boolean,
    useRocketPoolMode: boolean,
    priceDataEth: PricesResponse,
    priceDataRpl: PricesResponse,
    groupByDate: boolean,
): void {
    let columns = groupByDate ? [
        "Date",
        `Price [${priceDataEth.currency}/ETH]`,
        "Consensus Layer Income [ETH]",
        "Execution Layer Income [ETH]",
    ] : [
        "Date",
        "Validator Index",
        `Price [${priceDataEth.currency}/ETH]`,
        "Consensus Layer Income [ETH]",
        "Execution Layer Income [ETH]",
    ]

    if (useRocketPoolMode) {
        if (!groupByDate) {
            columns.push("Node Address")
        }

        columns.push(...["Smoothing Pool Income [ETH]", "Rocket Pool Node Income [RPL]", `Price [${priceDataRpl.currency}/RPL]`])
    }

    let csvContent = columns.join(SEPARATOR);
    csvContent += "\n";

    const allDates = new Set<string>();

    for (const rewards of validatorRewardsData) {
        for (const reward of rewards.consensus_layer_rewards) {
            allDates.add(reward.date);
        }

        for (const reward of rewards.execution_layer_rewards) {
            allDates.add(reward.date);
        }

        for (const reward of rewards.withdrawals) {
            allDates.add(reward.date);
        }
    }

    for (const reward of rocketPoolNodeRewards) {
        allDates.add(reward.date)
    }

    for (const date of allDates) {
        if (groupByDate) {
            let consensusTotal = BigInt(0);
            let executionTotal = BigInt(0);
            let smoothingPoolTotal = BigInt(0);
            let rplIncomeTotal = BigInt(0);

            for (const rewards of validatorRewardsData) {
                const isRocketPoolValidator = useRocketPoolMode && isRocketPoolValidatorRewards(rewards);

                if (!useConsensusIncomeOnWithdrawal) {
                    for (const reward of rewards.consensus_layer_rewards) {
                        if (reward.date === date) {
                            if (isRocketPoolValidator) {
                                consensusTotal += getOperatorReward(
                                    (rewards as RocketPoolValidatorRewards).bonds,
                                    (rewards as RocketPoolValidatorRewards).fees,
                                    reward
                                ).amount_wei;
                            } else {
                                consensusTotal += reward.amount_wei;
                            }
                            break;
                        }
                    }
                } else {
                    for (const reward of rewards.withdrawals) {
                        if (reward.date === date) {
                            if (isRocketPoolValidator) {
                                consensusTotal += getOperatorReward(
                                    (rewards as RocketPoolValidatorRewards).bonds,
                                    (rewards as RocketPoolValidatorRewards).fees,
                                    reward
                                ).amount_wei;
                            } else {
                                consensusTotal += reward.amount_wei;
                            }
                            break;
                        }
                    }
                }

                for (const reward of rewards.execution_layer_rewards) {
                    if (reward.date === date) {
                        if (isRocketPoolValidator) {
                            executionTotal += getOperatorReward(
                                (rewards as RocketPoolValidatorRewards).bonds,
                                (rewards as RocketPoolValidatorRewards).fees,
                                reward
                            ).amount_wei;
                        } else {
                            executionTotal += reward.amount_wei;
                        }
                        break;
                    }
                }
            }

            for (const reward of rocketPoolNodeRewards) {
                if (reward.date === date) {
                    smoothingPoolTotal += reward.amount_wei;
                    rplIncomeTotal += reward.amount_rpl
                }
            }

            const columnValues = [
                `${date}`,
                `${getPriceForDate(priceDataEth.prices, date)}`,
                `${Number(consensusTotal / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                `${Number(executionTotal / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
            ]

            if (useRocketPoolMode) {
                columnValues.push(...[
                    (Number(smoothingPoolTotal / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)).toString(),
                    (Number(rplIncomeTotal / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)).toString(),
                    getPriceForDate(priceDataRpl.prices, date).toString(),
                ])
            }

            csvContent += columnValues.join(SEPARATOR);
            csvContent += "\n";
        } else {
            for (const rewards of validatorRewardsData) {
                const validatorIndex = rewards.validator_index;
                const isRocketPoolValidator = useRocketPoolMode && isRocketPoolValidatorRewards(rewards);

                let consensusReward: RewardForDate;
                if (useConsensusIncomeOnWithdrawal) {
                    consensusReward = getRewardForDate(rewards.withdrawals, date, isRocketPoolValidator, rewards);
                } else {
                    consensusReward = getRewardForDate(rewards.consensus_layer_rewards, date, isRocketPoolValidator, rewards);
                }
                let executionReward = getRewardForDate(rewards.execution_layer_rewards, date, isRocketPoolValidator, rewards);

                const columnValues = [
                    `${date}`,
                    `${validatorIndex}`,
                    `${getPriceForDate(priceDataEth.prices, date)}`,
                    `${Number(consensusReward.amount_wei / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                    `${Number(executionReward.amount_wei / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                ]
                if (useRocketPoolMode) {
                    columnValues.push(...["", "", "", ""])
                }
                csvContent += columnValues.join(SEPARATOR);
                csvContent += "\n";
            }

            if (useRocketPoolMode) {
                for (const reward of rocketPoolNodeRewards) {
                    if (reward.date !== date) continue

                    const columnValues = [
                        `${date}`,
                        "", // Validator Index
                        `${getPriceForDate(priceDataEth.prices, date)}`,
                        "", // Consensus Layer
                        "", // Execution Layer
                        `${reward.node_address}`,
                        `${Number(reward.amount_wei / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                        `${Number(reward.amount_rpl / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                        `${getPriceForDate(priceDataRpl.prices, date)}`,
                    ]
                    csvContent += columnValues.join(SEPARATOR);
                    csvContent += "\n";
                }
            }
        }
    }

    createLinkAndDownload(csvContent);
}

function getPriceForDate(prices: PriceForDate[], date: string): number {
    const matchingPrice = prices.find(price => price.date === date);
    if (!matchingPrice) throw `Failed to find price for date ${date}`;
    return matchingPrice.price;
}

function getRewardForDate(rewards: RewardForDate[], date: string, isRocketPoolValidator: boolean, allRewardsData: ValidatorRewards | RocketPoolValidatorRewards): RewardForDate {
    const fullRewardForDate = rewards.find(reward => reward.date === date)  ?? { amount_wei: 0n, date: date};
    if (isRocketPoolValidator) {
        return getOperatorReward(
            (allRewardsData as RocketPoolValidatorRewards).bonds,
            (allRewardsData as RocketPoolValidatorRewards).fees,
            fullRewardForDate);
    } else {
        return fullRewardForDate;
    }

}
