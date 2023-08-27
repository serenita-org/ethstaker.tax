import {PriceForDate, PricesResponse, RewardForDate, ValidatorRewards} from "../../types/rewards.ts";
import { gweiToEthMultiplier, WeiToGweiMultiplier } from "../../constants.ts";

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

export function downloadAsCsv(rewardsData: ValidatorRewards[], priceData: PricesResponse, groupByDate: boolean): void {
    let columns = groupByDate ? [
        "Date",
        `Price [${priceData.currency}/ETH]`,
        "Consensus Layer Income",
        "Execution Layer Income",
        "Withdrawals",
    ] : [
        "Date",
        "Validator Index",
        `Price [${priceData.currency}/ETH]`,
        "Consensus Layer Income",
        "Execution Layer Income",
        "Withdrawals",
    ]

    let csvContent = columns.join(SEPARATOR);
    csvContent += "\n";

    const allDates = new Set<string>();

    for (const rewards of rewardsData) {
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

    for (const date of allDates) {
        if (groupByDate) {
            let consensusTotal = BigInt(0);
            let executionTotal = BigInt(0);
            let withdrawalTotal = BigInt(0);

            for (const rewards of rewardsData) {
                for (const reward of rewards.consensus_layer_rewards) {
                    if (reward.date === date) {
                        consensusTotal += reward.amount_wei;
                        break;
                    }
                }

                for (const reward of rewards.execution_layer_rewards) {
                    if (reward.date === date) {
                        executionTotal += reward.amount_wei;
                        break;
                    }
                }

                for (const reward of rewards.withdrawals) {
                    if (reward.date === date) {
                        withdrawalTotal += reward.amount_wei;
                        break;
                    }
                }
            }

            const columnValues = [
                `${date}`,
                `${getPriceForDate(priceData.prices, date)}`,
                `${Number(consensusTotal / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                `${Number(executionTotal / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                `${Number(withdrawalTotal / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
            ]
            csvContent += columnValues.join(SEPARATOR);
            csvContent += "\n";
        } else {
            for (const rewards of rewardsData) {
                const validatorIndex = rewards.validator_index;

                const consensusReward = getRewardForDate(rewards.consensus_layer_rewards, date);
                const executionReward = getRewardForDate(rewards.execution_layer_rewards, date);
                const withdrawalReward = getRewardForDate(rewards.withdrawals, date);

                const columnValues = [
                    `${date}`,
                    `${validatorIndex}`,
                    `${getPriceForDate(priceData.prices, date)}`,
                    `${Number(consensusReward / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                    `${Number(executionReward / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                    `${Number(withdrawalReward / WeiToGweiMultiplier) / Number(gweiToEthMultiplier)}`,
                ]
                csvContent += columnValues.join(SEPARATOR);
                csvContent += "\n";
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

function getRewardForDate(rewards: RewardForDate[], date: string): bigint {
    const matchingReward = rewards.find(reward => reward.date === date);
    return matchingReward ? matchingReward.amount_wei : BigInt(0);
}
