<template>
  <table class="table table-bordered border-primary p-3" style="background-color: transparent">
    <thead>
      <tr>
        <th scope="col" style="background-color: transparent"></th>
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
import {PricesResponse, ValidatorRewards} from "../../types/rewards.ts";
import {gweiToEthMultiplier, WeiToEthMultiplier, WeiToGweiMultiplier} from "../../constants.ts";

const props = defineProps({
  rewardsData: Object as PropType<ValidatorRewards[]>,
  priceData: Object as PropType<PricesResponse>,
  currency: String,
});

function aggregateRewardsData(key: string): [number, number] {
  const sumRewardsEthWei = props.rewardsData?.reduce((total, validatorData) => {
      const keyRewardsTotal = validatorData[key].reduce((totalForValidator, reward) => {
        return totalForValidator + reward.amount_wei;
      }, BigInt(0));
      return total + keyRewardsTotal;
  }, BigInt(0));
  const sumConsensusRewardsCurr = props.rewardsData?.reduce((total, validatorData) => {
      const keyRewardsTotal = validatorData[key].reduce((totalForValidator, reward) => {
          return totalForValidator + reward.amount_wei * BigInt(100 * props.priceData?.prices.find(price => price.date == reward.date).price);
      }, BigInt(0));
      return total + keyRewardsTotal;
  }, BigInt(0));

  // sumRewardsEthWei is in wei - a BigInt
  // -> Get to Gwei precision (this will round off smaller units).
  // At that point we can use JS numbers
  const sumRewardsEth_Gwei = sumRewardsEthWei / BigInt(WeiToGweiMultiplier);
  if (sumRewardsEth_Gwei > Number.MAX_SAFE_INTEGER) throw `sumRewardsEth_Gwei (${sumRewardsEth_Gwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
  const sumRewardsCurrCents = sumConsensusRewardsCurr / (BigInt(1e18))
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
  background-color: rgba(var(--serenita-green-dark), 0.25);
}

</style>
