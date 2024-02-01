<template>
  <table class="table text-center">
    <thead>
      <tr>
        <th scope="col"></th>
        <th scope="col">ETH</th>
        <th v-if="useRocketPoolMode" scope="col">RPL</th>
        <th scope="col">{{ currency }}</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <th scope="row">
          Consensus Layer Income
          <i
              v-if="useRocketPoolMode"
              class="bi-question-square"
              v-b-tooltip
              title="Shows your part of the CL income that was withdrawn to your minipool contract addresses"
          />
        </th>
        <td>{{ formatZero(totalConsensusLayerIncome[0], 6) }}</td>
        <td v-if="useRocketPoolMode">0</td>
        <td>{{ formatZero(totalConsensusLayerIncome[1], 3) }}</td>
      </tr>
      <tr>
        <th scope="row">
          Execution Layer Income
          <i
              v-if="useRocketPoolMode"
              class="bi-question-square"
              v-b-tooltip
              title="Shows your part of the EL income that went to your node's fee distributor contract"
          />
        </th>
        <td>{{ formatZero(totalExecutionLayerIncome[0], 6) }}</td>
        <td v-if="useRocketPoolMode">0</td>
        <td>{{ formatZero(totalExecutionLayerIncome[1], 3) }}</td>
      </tr>
      <tr v-if="useRocketPoolMode">
        <th scope="row">
          Smoothing Pool Income
          <i
              v-if="useRocketPoolMode"
              class="bi-question-square"
              v-b-tooltip
              title="This is income at the Rocket Pool node level, spread across all node minipools"
          />
        </th>
        <td>{{ formatZero(totalSmoothingPoolIncome[0], 6) }}</td>
        <td>0</td>
        <td>{{ formatZero(totalSmoothingPoolIncome[1], 3) }}</td>
      </tr>
      <tr v-if="useRocketPoolMode">
        <th scope="row">
          RPL Income
          <i
              v-if="useRocketPoolMode"
              class="bi-question-square"
              v-b-tooltip
              title="This is income at the Rocket Pool node level, spread across all node minipools"
          />
        </th>
        <td>0</td>
        <td>{{ formatZero(totalRplIncome[0], 6) }}</td>
        <td>{{ formatZero(totalRplIncome[1], 3) }}</td>
      </tr>
    </tbody>
    <tfoot>
      <tr class="fw-bold">
        <th scope="row">Total</th>
        <td>{{ formatZero(totalConsensusLayerIncome[0] + totalExecutionLayerIncome[0] + totalSmoothingPoolIncome[0], 6) }}</td>
        <td v-if="useRocketPoolMode">{{ formatZero(totalRplIncome[0], 6) }}</td>
        <td>{{ formatZero(totalConsensusLayerIncome[1] + totalExecutionLayerIncome[1] + totalSmoothingPoolIncome[1] + totalRplIncome[1], 3) }}</td>
      </tr>
    </tfoot>
  </table>
</template>
<script setup lang="ts">

import {computed, PropType} from "vue";
import {
  PricesResponse,
  RewardForDate,
  RocketPoolNodeRewardForDate,
  RocketPoolValidatorRewards,
  ValidatorRewards, ValidatorRewardsBase
} from "../../types/rewards.ts";
import {gweiToEthMultiplier, WeiToEthMultiplier, WeiToGweiMultiplier} from "../../constants.ts";

const props = defineProps({
  validatorRewardsData: {
    type: Object as PropType<(ValidatorRewards | RocketPoolValidatorRewards)[]>,
    required: true,
  },
  rocketPoolNodeRewards: {
    type: Object as PropType<RocketPoolNodeRewardForDate[]>,
    required: true,
  },
  useConsensusIncomeOnWithdrawal: {
    type: Boolean,
    required: true,
  },
  useRocketPoolMode: {
    type: Boolean,
    required: true,
  },
  priceDataEth: {
    type: Object as PropType<PricesResponse>,
    required: true,
  },
  priceDataRpl: {
    type: Object as PropType<PricesResponse>,
    required: true,
  },
  currency: {
    type: String,
    required: true
  },
});

function formatZero(number: number, digits: number) {
  if (number === 0) {
    return "0"
  } else { return number.toFixed(digits) }
}

function aggregateRewardsData(key: keyof ValidatorRewardsBase): [number, number] {
  const aggregateValidatorRewardsSumWei = props.validatorRewardsData?.reduce((total, validatorData) => {
    const validatorRewardsSumWei = (validatorData[key] as RewardForDate[]).reduce((totalForValidator, reward) => {
      return totalForValidator + reward.amount_wei;
    }, BigInt(0));
    return total + validatorRewardsSumWei;
  }, BigInt(0));
  const aggregateValidatorRewardsSumCurr = props.validatorRewardsData?.reduce((total, validatorData) => {
    const validatorRewardsSumCurr = (validatorData[key] as RewardForDate[]).reduce((totalForValidator, reward) => {
      const priceData = props.priceDataEth.prices.find(price => price.date == reward.date);
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
  if (props.useConsensusIncomeOnWithdrawal) {
    return aggregateRewardsData("withdrawals");
  } else {
    return aggregateRewardsData("consensus_layer_rewards");
  }
})

const totalExecutionLayerIncome = computed<[number, number]>(() => {
  return aggregateRewardsData("execution_layer_rewards");
})

const totalSmoothingPoolIncome = computed<[number, number]>(() => {
  if (!props.useRocketPoolMode) return [0, 0];

  const smoothingPoolSumWei = props.rocketPoolNodeRewards.reduce((total, reward) => {
    return total + reward.amount_wei;
  }, BigInt(0));

  const smoothingPoolSumCurr = props.rocketPoolNodeRewards.reduce((total, reward) => {
      const priceData = props.priceDataEth.prices.find(price => price.date == reward.date);
      if (!priceData) throw `Price data not found for ${reward.date}`;
      return total + reward.amount_wei * BigInt((100 * priceData.price).toFixed(0));
  }, BigInt(0));

  const smoothingPoolSumGwei = smoothingPoolSumWei / BigInt(WeiToGweiMultiplier);
  if (smoothingPoolSumGwei > Number.MAX_SAFE_INTEGER) throw `smoothingPoolSumGwei (${smoothingPoolSumGwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
  const smoothingPoolSumCents = smoothingPoolSumCurr / (BigInt(WeiToEthMultiplier));
  if (smoothingPoolSumCents > Number.MAX_SAFE_INTEGER) throw `smoothingPoolSumCents (${smoothingPoolSumCents}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`

  return [
      Number(smoothingPoolSumGwei) / Number(gweiToEthMultiplier),
      Number(smoothingPoolSumCents) / 100,
  ];
})

const totalRplIncome = computed<[number, number]>(() => {
  const rplIncomeSumWei = props.rocketPoolNodeRewards.reduce((total, reward) => {
        return total + reward.amount_rpl;
  }, BigInt(0));

  const rplIncomeSumCurr = props.rocketPoolNodeRewards.reduce((total, reward) => {
      const priceData = props.priceDataRpl.prices.find(price => price.date == reward.date);
      if (!priceData) throw `Price data not found for ${reward.date}`;
      return total + reward.amount_rpl * BigInt((100 * priceData.price).toFixed(0));
  }, BigInt(0));

  const rplIncomeSumGwei = rplIncomeSumWei / BigInt(WeiToGweiMultiplier);
  if (rplIncomeSumGwei > Number.MAX_SAFE_INTEGER) throw `rplIncomeSumGwei (${rplIncomeSumGwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
  const rplIncomeSumCents = rplIncomeSumCurr / (BigInt(WeiToEthMultiplier));
  if (rplIncomeSumCents > Number.MAX_SAFE_INTEGER) throw `rplIncomeSumCents (${rplIncomeSumCents}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`

  return [
      Number(rplIncomeSumGwei) / Number(gweiToEthMultiplier),
      Number(rplIncomeSumCents) / 100,
  ];
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
