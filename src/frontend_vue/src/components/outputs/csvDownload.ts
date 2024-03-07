import BigNumber from "bignumber.js";
import {
    PriceForDate,
    PricesResponse,
    RewardForDate, RocketPoolNodeRewardForDate,
    RocketPoolValidatorRewards,
    ValidatorRewards
} from "../../types/rewards.ts";
import { WeiToEthMultiplier } from "../../constants.ts";


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

function weiToEthString(wei: string, decimalPlaces: number) {
    const weiBigInt = new BigNumber(wei);
    const ethDecimal = weiBigInt.dividedBy(WeiToEthMultiplier.toString());
    return ethDecimal.toFixed(decimalPlaces, BigNumber.ROUND_DOWN);
}

export function downloadAsCsv(
    validatorRewardsData: (ValidatorRewards|RocketPoolValidatorRewards)[],
    rocketPoolNodeRewards: RocketPoolNodeRewardForDate[],
    useConsensusIncomeOnWithdrawal: boolean,
    useRocketPoolMode: boolean,
    priceDataEth: PricesResponse,
    priceDataRpl: PricesResponse,
    groupByDate: boolean,
    delimiter: string,
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

    let csvContent = columns.join(delimiter);
    csvContent += "\n";

    const allDates = new Set<string>();

    for (const rewards of validatorRewardsData) {
        if (rewards.consensus_layer_rewards != null) {
            for (const reward of rewards.consensus_layer_rewards) {
                allDates.add(reward.date);
            }
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

    for (const date of Array.from(allDates).sort()) {
        if (groupByDate) {
            let consensusTotal = BigInt(0);
            let executionTotal = BigInt(0);
            let smoothingPoolTotal = BigInt(0);
            let rplIncomeTotal = BigInt(0);

            for (const rewards of validatorRewardsData) {
                if (!useConsensusIncomeOnWithdrawal) {
                    if (rewards.consensus_layer_rewards == null) {
                        const errorMessage = "Must use withdrawal option for Rocket Pool validators!";
                        alert(errorMessage);
                        throw errorMessage;
                    }
                    for (const reward of rewards.consensus_layer_rewards) {
                        if (reward.date === date) {
                            consensusTotal += reward.amount_wei;
                            break;
                        }
                    }
                } else {
                    for (const reward of rewards.withdrawals) {
                        if (reward.date === date) {
                            consensusTotal += reward.amount_wei;
                            break;
                        }
                    }
                }

                for (const reward of rewards.execution_layer_rewards) {
                    if (reward.date === date) {
                        executionTotal += reward.amount_wei;
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

            if ((consensusTotal + executionTotal + smoothingPoolTotal + rplIncomeTotal) === BigInt(0)) {
                continue
            }

            const columnValues = [
                `${date}`,
                `${getPriceForDate(priceDataEth.prices, date)}`,
                `${weiToEthString(consensusTotal.toString(), 9)}`,
                `${weiToEthString(executionTotal.toString(), 18)}`,
            ]

            if (useRocketPoolMode) {
                columnValues.push(...[
                    weiToEthString(smoothingPoolTotal.toString(), 18),
                    weiToEthString(rplIncomeTotal.toString(), 18),
                    getPriceForDate(priceDataRpl.prices, date).toString(),
                ])
            }

            csvContent += columnValues.join(delimiter);
            csvContent += "\n";
        } else {
            for (const rewards of validatorRewardsData) {
                const validatorIndex = rewards.validator_index;

                let consensusReward: RewardForDate;
                if (useConsensusIncomeOnWithdrawal) {
                    consensusReward = getRewardForDate(rewards.withdrawals, date);
                } else {
                    if (rewards.consensus_layer_rewards == null) {
                        const errorMessage = "Must use withdrawal option for Rocket Pool validators!";
                        alert(errorMessage);
                        throw errorMessage;
                    }
                    consensusReward = getRewardForDate(rewards.consensus_layer_rewards, date);
                }
                let executionReward = getRewardForDate(rewards.execution_layer_rewards, date);

                if (consensusReward.amount_wei === BigInt(0) && executionReward.amount_wei === BigInt(0)) {
                    continue
                }

                const columnValues = [
                    `${date}`,
                    `${validatorIndex}`,
                    `${getPriceForDate(priceDataEth.prices, date)}`,
                    `${weiToEthString(consensusReward.amount_wei.toString(), 9)}`,
                    `${weiToEthString(executionReward.amount_wei.toString(), 18)}`,
                ]
                if (useRocketPoolMode) {
                    columnValues.push(...["", "", "", ""])
                }
                csvContent += columnValues.join(delimiter);
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
                        `${weiToEthString(reward.amount_wei.toString(), 18)}`,
                        `${weiToEthString(reward.amount_rpl.toString(), 18)}`,
                        `${getPriceForDate(priceDataRpl.prices, date)}`,
                    ]
                    csvContent += columnValues.join(delimiter);
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

function getRewardForDate(rewards: RewardForDate[], date: string): RewardForDate {
    return rewards.find(reward => reward.date === date)  ?? { amount_wei: 0n, date: date};
}
