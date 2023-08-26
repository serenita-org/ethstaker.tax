<script setup lang="ts">
import { ref } from 'vue'
import ValidatorAdder from "../components/calculator/ValidatorAdder.vue";
import CurrencyPicker from "../components/calculator/CurrencyPicker.vue";
import DateRangePicker from "../components/calculator/DateRangePicker.vue";

const validatorIndexes = ref(new Set());
const startDateString = ref();
const endDateString = ref();

</script>

<template>
  <div class="container my-3">
    <h1>Add your validators</h1>
    <ValidatorAdder @validators-changed="(newValidatorIndexes: Set<number>) => validatorIndexes = newValidatorIndexes"></ValidatorAdder>
  </div>
  <div class="container my-3">
    <div class="row">
      <div class="col">
        <h1>Date range</h1>
        <DateRangePicker @date-range-changed="(newStartDate: string, newEndDate: string) => { startDateString = newStartDate; endDateString = newEndDate }"></DateRangePicker>
      </div>
      <div class="col">
        <h1>Currency</h1>
        <CurrencyPicker></CurrencyPicker>
      </div>
    </div>
  </div>
</template>

<style scoped>

h1 {
  margin-bottom: 1rem;
}

</style>
