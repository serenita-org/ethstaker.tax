<template>
  <table class="table border-primary">
    <thead>
      <tr>
        <th scope="col"></th>
        <th scope="col">ETH</th>
        <th scope="col">{{ currency }}</th>
      </tr>
    </thead>
    <tbody class="text-center">
      <tr>
        <th scope="row">Consensus Layer Income</th>
        <td>{{ totalConsensusLayerIncome[0].toFixed(6) }}</td>
        <td>{{ totalConsensusLayerIncome[1].toFixed(3) }}</td>
      </tr>
      <tr>
        <th scope="row">Execution Layer Income</th>
        <td>{{ totalExecutionLayerIncome[0].toFixed(6) }}</td>
        <td>{{ totalExecutionLayerIncome[1].toFixed(3) }}</td>
      </tr>
    </tbody>
    <tfoot>
      <tr class="fw-bold">
        <th scope="row">Total</th>
        <td>{{ (totalConsensusLayerIncome[0] + totalExecutionLayerIncome[0] ).toFixed(6) }}</td>
        <td>{{ (totalConsensusLayerIncome[1] + totalExecutionLayerIncome[1] ).toFixed(3) }}</td>
      </tr>
    </tfoot>
  </table>
</template>
<script setup lang="ts">

import {computed, PropType} from "vue";
import {PricesResponse, RewardForDate, ValidatorRewards} from "../../types/rewards.ts";
import {gweiToEthMultiplier, WeiToEthMultiplier, WeiToGweiMultiplier} from "../../constants.ts";

const props = defineProps({
  rewardsData: {
    type: Object as PropType<ValidatorRewards[]>,
    required: true,
  },
  priceData: {
    type: Object as PropType<PricesResponse>,
    required: true,
  },
  currency: {
    type: String,
    required: true
  },
});

function aggregateRewardsData(key: keyof ValidatorRewards): [number, number] {
  const aggregateValidatorRewardsSumWei = props.rewardsData?.reduce((total, validatorData: ValidatorRewards) => {
      const validatorRewardsSumWei = (validatorData[key] as RewardForDate[]).reduce((totalForValidator, reward) => {
        return totalForValidator + reward.amount_wei;
      }, BigInt(0));
      return total + validatorRewardsSumWei;
  }, BigInt(0));
  const aggregateValidatorRewardsSumCurr = props.rewardsData?.reduce((total, validatorData) => {
      const validatorRewardsSumCurr = (validatorData[key] as RewardForDate[]).reduce((totalForValidator, reward) => {
        const priceData = props.priceData.prices.find(price => price.date == reward.date);
        if (!priceData) throw `Price data not found for ${reward.date}`;
          return totalForValidator + reward.amount_wei * BigInt((100 * priceData.price).toFixed(0));
      }, BigInt(0));
      return total + validatorRewardsSumCurr;
  }, BigInt(0));

  if (aggregateValidatorRewardsSumWei == undefined) throw "aggregateValidatorRewardsSumWei is undefined"
  if (aggregateValidatorRewardsSumCurr == undefined) throw "aggregateValidatorRewardsSumCurr is undefined"

  // aggregateValidatorRewardsSumWei is in wei - a BigInt
  // -> Get to Gwei precision (this will round off smaller units).
  // At that point we can use JS numbers
  const sumRewardsEth_Gwei = aggregateValidatorRewardsSumWei / BigInt(WeiToGweiMultiplier);
  if (sumRewardsEth_Gwei > Number.MAX_SAFE_INTEGER) throw `sumRewardsEth_Gwei (${sumRewardsEth_Gwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
  const sumRewardsCurrCents = aggregateValidatorRewardsSumCurr / (BigInt(WeiToEthMultiplier))
  if (sumRewardsCurrCents > Number.MAX_SAFE_INTEGER) throw `sumRewardsCurrCents (${sumRewardsCurrCents}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`

  return [
      Number(sumRewardsEth_Gwei) / Number(gweiToEthMultiplier),
      Number(sumRewardsCurrCents) / 100
  ];
}

const totalConsensusLayerIncome = computed<[number, number]>(() => {
  return aggregateRewardsData("consensus_layer_rewards");
})

const totalExecutionLayerIncome = computed<[number, number]>(() => {
  return aggregateRewardsData("execution_layer_rewards");
})

</script>

<style scoped>

th, td {
  background-color: transparent;
  border-style: none;
}
thead th:first-child {
 border-top-left-radius: 9px;
}

thead th:last-child {
 border-top-right-radius: 9px;
}

tfoot tr:last-child :first-child {
 border-bottom-left-radius: 9px;
}

tfoot tr:last-child :last-child {
 border-bottom-right-radius: 9px;
}
</style>
