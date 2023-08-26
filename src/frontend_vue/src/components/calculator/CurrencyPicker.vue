<script setup lang="ts">
import {onMounted, ref} from "vue";
import axios from "axios";

const supportedCurrenciesUrl = new URL("https://ethstaker.tax/api/v1/supported_currencies", window.location.href);

const supportedCurrencies = ref([]);

const dataLoading = ref(true);

onMounted(async () => {
  try {
   const resp = await axios.get(supportedCurrenciesUrl.toString());
   supportedCurrencies.value = resp.data;
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
    <select class="form-select">
      <option v-for="currency of supportedCurrencies" :selected="currency == 'USD'">{{ currency }}</option>
    </select>
  </div>
</template>
