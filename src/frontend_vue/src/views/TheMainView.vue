<script setup lang="ts">
import {computed, Ref, ref, watch} from 'vue'
import ValidatorAdder from "../components/inputs/ValidatorAdder.vue";
import CurrencyPicker from "../components/inputs/CurrencyPicker.vue";
import DateRangePicker from "../components/inputs/DateRangePicker.vue";
import {
  PricesRequestParams,
  PricesResponse,
  RewardsRequest, RewardsResponse, RocketPoolNodeRewardForDate, RocketPoolValidatorRewards,
  ValidatorRewards,
} from "../types/rewards.ts";
import { parse, isInteger } from 'lossless-json'
import { downloadAsCsv } from '../components/outputs/csvDownload.ts'

import axios, {AxiosError} from "axios";
import IncomeChart from "../components/outputs/IncomeChart.vue";
import SummaryTable from "../components/outputs/SummaryTable.vue";

let validatorIndexes: Ref<Set<number>> = ref(new Set([]));
let selectedCurrency = ref();
let startDateString = ref();
let endDateString = ref();

let rocketPoolNodeRewards: Ref<(RocketPoolNodeRewardForDate)[]> = ref([]);
let validatorRewardsData: Ref<(ValidatorRewards | RocketPoolValidatorRewards)[]> = ref([]);
let rewardsLoading = ref(false);

let priceDataEth: Ref<PricesResponse | undefined> = ref();
let priceDataRpl: Ref<PricesResponse | undefined> = ref();
let priceDataLoading = ref(false);


watch(selectedCurrency, async () => {
  if (validatorRewardsData.value.length == 0) return;
  await getPriceData();
})
watch(validatorRewardsData, async () => {
  if (validatorRewardsData.value.length == 0) return;
  await getPriceData();
})


async function getPriceData() {
  const pricesRequestParams: PricesRequestParams = {
    start_date: startDateString.value,
    end_date: endDateString.value,
    currency: selectedCurrency.value,
  }

  priceDataEth.value = undefined;
  priceDataRpl.value = undefined;
  priceDataLoading.value = true;

  try {
    const respEth = await axios.get("/api/v2/prices/ethereum", { params: pricesRequestParams });
    priceDataEth.value = respEth.data;
    const respRpl = await axios.get("/api/v2/prices/rocket-pool", { params: pricesRequestParams });
    priceDataRpl.value = respRpl.data;
  } catch (err: unknown) {
    let errorMessage: string
    if (axios.isAxiosError(err)) {
      errorMessage = `Failed to get prices - ${err.message}`;
    } else {
      errorMessage = `Unknown error occurred - ${err}`;
    }
    alert(errorMessage);
    throw err;
  } finally {
    priceDataLoading.value = false;
  }
}

async function getRewards() {
  const data: RewardsRequest = {
    validator_indexes: Array.from(validatorIndexes.value),
    start_date: startDateString.value,
    end_date: endDateString.value,
  }

  rocketPoolNodeRewards.value = [];
  validatorRewardsData.value = [];
  rewardsLoading.value = true;

  // parse integer values into a bigint, and use a regular number otherwise
  function customNumberParser(value: string) {
    // Ran into some issues using the default LosslessNumber type -> using BigInt
    return isInteger(value) ? BigInt(value) : parseFloat(value)
  }

  try {
    const resp: RewardsResponse = (await axios.post("/api/v2/rewards", data, {
      transformResponse: function (response) {
        // Parse using lossless-json library - the amounts are in wei and could be larger
        // than JS
        return parse(response, undefined, customNumberParser);
      }
    })).data;
    rocketPoolNodeRewards.value = resp.rocket_pool_node_rewards;
    validatorRewardsData.value = resp.validator_rewards;
  } catch (err: unknown) {
    let errorMessage: string
    if (axios.isAxiosError(err)) {
      errorMessage = `Failed to get rewards - ${(err as AxiosError).message}`;
    } else {
      errorMessage = `Unknown error occurred - ${err}`;
    }
    alert(errorMessage);
    throw err;
  } finally {
    rewardsLoading.value = false;
  }
}

const showOutputs = computed<boolean>(() => {
  if (validatorRewardsData.value.length == 0) return false;
  if (!priceDataEth.value) return false;
  if (!priceDataRpl.value) return false;
  if (priceDataEth.value?.prices.length == 0) return false;
  if (priceDataRpl.value?.prices.length == 0) return false;
  return true;
})

</script>

<template>
  <div class="container my-3">
    <h2>Add your validators here</h2>
    <ValidatorAdder @validator-indexes-changed="(newValidatorIndexes: Set<number>) => validatorIndexes = newValidatorIndexes"></ValidatorAdder>
  </div>
  <div class="container my-3">
    <div class="row">
      <div class="col">
        <h3>Pick a date range</h3>
        <DateRangePicker @date-range-changed="(newStartDate: string, newEndDate: string) => { startDateString = newStartDate; endDateString = newEndDate }"></DateRangePicker>
      </div>
      <div class="col">
        <h3>Select your currency</h3>
        <CurrencyPicker @selected-currency-changed="(newCurrency: string) => {selectedCurrency = newCurrency}"></CurrencyPicker>
      </div>
    </div>
  </div>
  <div class="container my-3 text-center">
    <BButton
        variant="primary"
        @click.prevent="getRewards"
        :disabled="validatorIndexes.size == 0 || rewardsLoading"
        class="mx-1"
    >
      <div v-if="rewardsLoading" class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <span v-else>
        <i class="bi-calculator"></i>
        Calculate
      </span>
    </BButton>
    <BButton
        class="mx-1"
        @click="downloadAsCsv(
            validatorRewardsData,
            rocketPoolNodeRewards,
            priceDataEth as PricesResponse,
            priceDataRpl as PricesResponse,
            ($refs['groupByDateCheckbox'] as HTMLInputElement).checked
            )"
        :disabled="validatorRewardsData.length == 0 || !priceDataEth"
        variant="secondary"
    >
      <span>
        <i class="bi-cloud-download"></i>
        Download CSV for all validators
      </span>
    </BButton>
    <div class="form-check form-check-inline mx-1">
      <input ref="groupByDateCheckbox" class="form-check-input" id="groupByDateCheckbox" type="checkbox">
      <label class="form-check-label" for="groupByDateCheckbox">Group By Date</label>
    </div>
  </div>
  <div class="container mt-3 mb-5">
    <div
      v-if="showOutputs"
      class="row d-flex align-items-center"
    >
      <div class="col-lg-6">
        <IncomeChart
            :rewards-data="validatorRewardsData"
            :price-data="priceDataEth"
            :currency="selectedCurrency"
            chart-container-height="300px"
            chart-container-width="100%"
        >
        </IncomeChart>
      </div>
      <div class="col-lg-6">
        <SummaryTable
            :validator-rewards-data="validatorRewardsData"
            :rocket-pool-node-rewards="rocketPoolNodeRewards"
            :price-data-eth="priceDataEth"
            :price-data-rpl="priceDataRpl"
            :currency="selectedCurrency"
        >
        </SummaryTable>
      </div>
    </div>
  </div>
</template>

<style scoped>

h1 {
  margin-bottom: 1rem;
}

</style>
