<script setup lang="ts">
import {Ref, ref, watch} from 'vue'
import ValidatorAdder from "../components/inputs/ValidatorAdder.vue";
import CurrencyPicker from "../components/inputs/CurrencyPicker.vue";
import DateRangePicker from "../components/inputs/DateRangePicker.vue";
import {
  PricesRequestParams,
  PricesResponse,
  RewardsRequest,
  ValidatorRewards,
} from "../types/rewards.ts";
import { parse, isInteger } from 'lossless-json'
import { downloadAsCsv } from '../components/outputs/csvDownload.ts'

import axios from "axios";
import IncomeChart from "../components/outputs/IncomeChart.vue";
import SummaryTable from "../components/outputs/SummaryTable.vue";

let validatorIndexes: Ref<Set<number>> = ref(new Set([]));
let selectedCurrency = ref();
let startDateString = ref();
let endDateString = ref();

let rewardsData: Ref<ValidatorRewards[]> = ref([]);
let rewardsDataLoading = ref(false);

let priceData: Ref<PricesResponse | undefined> = ref();
let priceDataLoading = ref(false);


watch(selectedCurrency, async () => {
  if (rewardsData.value.length == 0) return;
  await getPriceData();
})
watch(rewardsData, async () => {
  if (rewardsData.value.length == 0) return;
  await getPriceData();
})


async function getPriceData() {
  const pricesRequestParams: PricesRequestParams = {
    start_date: startDateString.value,
    end_date: endDateString.value,
    currency: selectedCurrency.value,
  }

  priceData.value = undefined;
  priceDataLoading.value = true;

  try {
    const resp = await axios.get("https://ethstaker.tax/api/v2/prices", { params: pricesRequestParams });
    priceData.value = resp.data;
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

async function getRewardsData() {
  const data: RewardsRequest = {
    validator_indexes: Array.from(validatorIndexes.value),
    start_date: startDateString.value,
    end_date: endDateString.value,
  }

  rewardsData.value = [];
  rewardsDataLoading.value = true;

  // parse integer values into a bigint, and use a regular number otherwise
  function customNumberParser(value: string) {
    // Ran into some issues using the default LosslessNumber type -> using BigInt
    return isInteger(value) ? BigInt(value) : parseFloat(value)
  }

  try {
    const resp = await axios.post("https://ethstaker.tax/api/v2/rewards", data, {
      transformResponse: function (response) {
        // Parse using lossless-json library - the amounts are in wei and could be larger
        // than JS
        return parse(response, undefined, customNumberParser);
      }
    });
    rewardsData.value = resp.data;
  } catch (err: unknown) {
    let errorMessage: string
    if (axios.isAxiosError(err)) {
      errorMessage = `Failed to get rewards - ${err.message}`;
    } else {
      errorMessage = `Unknown error occurred - ${err}`;
    }
    alert(errorMessage);
    throw err;
  } finally {
    rewardsDataLoading.value = false;
  }
}

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
        @click.prevent="getRewardsData"
        :disabled="validatorIndexes.size == 0 || rewardsDataLoading"
        class="mx-1"
    >
      <div v-if="rewardsDataLoading" class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <span v-else>
        <i class="bi-calculator"></i>
        Calculate
      </span>
    </BButton>
    <BButton
        class="mx-1"
        @click="downloadAsCsv(rewardsData, priceData as PricesResponse, ($refs['groupByDateCheckbox'] as HTMLInputElement).checked)"
        :disabled="rewardsData.length == 0 || !priceData"
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
    <div class="row text-center">
      <div class="col-md-6">
        <IncomeChart
            v-if="rewardsData.length > 0"
            :rewards-data="rewardsData"
            chart-container-width="100%">
        </IncomeChart>
      </div>
      <div class="col-md-6">
        <SummaryTable
            v-if="rewardsData.length > 0 && priceData && priceData.prices.length > 0"
            :rewards-data="rewardsData"
            :price-data="priceData"
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
