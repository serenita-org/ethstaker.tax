<script setup lang="ts">
import {onMounted, ref} from "vue";
import axios from "axios";

const supportedCurrenciesUrl = new URL("https://ethstaker.tax/api/v1/supported_currencies", window.location.href);

const supportedCurrencies = ref([]);

const dataLoading = ref(true);
const selectedCurrency = ref("USD");

const emit = defineEmits(["selected-currency-changed"])

onMounted(async () => {
  try {
   const resp = await axios.get(supportedCurrenciesUrl.toString());
   supportedCurrencies.value = resp.data;
   emit('selected-currency-changed', selectedCurrency);
  } catch (e) {
    const errorMessage = `Failed to retrieve supported currencies!`;
    alert(errorMessage);
    throw errorMessage
  } finally {
    dataLoading.value = false;
  }
})

</script>

<template>
  <div v-if="!dataLoading">
    <select @change="$emit('selected-currency-changed', selectedCurrency)" v-model="selectedCurrency" class="form-select">
      <option v-for="currency of supportedCurrencies">{{ currency }}</option>
    </select>
  </div>
</template>
