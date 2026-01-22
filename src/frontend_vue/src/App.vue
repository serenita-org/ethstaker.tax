<script setup lang="ts">
import "bootstrap";
import TheMainView from './views/TheMainView.vue'

import { ref } from 'vue'

const gitcoinRoundActive = ref(false);
const gitcoinGrantLink = ref("https://explorer.gitcoin.co/#/round/10/0x8de918f0163b2021839a8d84954dd7e8e151326d/0x8de918f0163b2021839a8d84954dd7e8e151326d-37");

</script>

<template>
  <div class="my-3 alert alert-info" role="alert">
    ethstaker.tax is looking for maintainers. If you speak Python, understand Ethereum validators and would like to help keep this website alive, please reach out at info@serenita.io , u/eth2353 on Reddit or Luca on the EthStaker Discord.
  </div>
  <div class="mt-1 alert alert-info" role="alert">
    Please note 2025 will be the last year I'll personally be "officially" supporting.
  </div>
  <div class="container-fluid d-flex align-items-center justify-content-end mb-1">
      <h6 class="fw-light mx-2">ETHSTAKER.TAX</h6>
      <h6 class="fw-light mx-2">BY</h6>
      <a href="https://serenita.io/" target="_blank">
        <img src="./assets/logo-serenita.svg" class="logo serenita" alt="Logo Serenita" />
      </a>
  </div>
  <div v-if="gitcoinRoundActive" class="text-center bg-secondary py-1">
    <p class="text-muted my-2">ethstaker.tax is part of an ongoing Gitcoin matching round, please consider donating <a :href=gitcoinGrantLink target="_blank">here</a> to support this website!</p>
    <p class="text-muted my-2">During a Gitcoin matching round, even donating 1$ can have a big impact. Thank you!</p>
  </div>
  <TheMainView></TheMainView>
</template>

<style scoped>

h6 {
  margin: 0;
  text-align: center;
}

.logo {
  height:4em;
  will-change: filter;
  transition: filter 300ms;
}
.logo.serenita:hover {
  filter: drop-shadow(0 0 2em rgba(9, 134, 134, 0.75));
}

.bg-secondary {
  --bs-bg-opacity: 0.25;
}

</style>
