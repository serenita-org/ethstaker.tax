<script setup lang="ts">
import {Ref, ref, watch} from 'vue'
import axios from "axios";


const pubKeyUrl = new URL("https://ethstaker.tax/api/v1/index_for_publickey", window.location.href);
const depositAddrUrl = new URL("https://ethstaker.tax/api/v1/indexes_for_eth1_address", window.location.href);


const indexesInput = ref("");
const pubkeysInput = ref("");
const depositAddressesInput = ref("");

const validatorIndexes: Ref<Set<number>> = ref(new Set([]));

const emit = defineEmits<{
  (e: 'validator-indexes-changed', id: Set<number>): void
}>()

watch(validatorIndexes.value, async (newValidatorIndexes) => {
  emit('validator-indexes-changed', newValidatorIndexes);
})


function parseValidatorIndexes() {
  const inputIndexes = indexesInput.value.split(",").filter(Number).map(function(item) {
    return parseInt(item.trim());
  });
  inputIndexes.forEach(value => {
    validatorIndexes.value.add(value)
  });
}


async function getIndexesForPubkeys() {
  const inputPubkeys = pubkeysInput.value.split(",").map(function(item) {
    return item.trim();
  });

  for (const pubkey of [...new Set(inputPubkeys)]) {
    const resp = await axios.get(pubKeyUrl.toString(), { params: {
      publickey: pubkey
    }});

    if (resp.status !== 200) {
      const errorMessage = `Failed to get indexes for pubkey ${pubkey}!`;
      alert(errorMessage);
      throw errorMessage;
    }
    validatorIndexes.value.add(resp.data);
  }
}

async function getIndexesForDepositAddresses() {
  const inputDepositAddresses = depositAddressesInput.value.split(",").map(function(item) {
    return item.trim();
  });

  for (const depositAddress of [...new Set(inputDepositAddresses)]) {
    const resp = await axios.get(depositAddrUrl.toString(), { params: {
      eth1_address: depositAddress
    }});

    if (resp.status !== 200) {
      const errorMessage = `Failed to get indexes for deposit address ${depositAddress}!`;
      alert(errorMessage);
      throw errorMessage;
    }
    resp.data.forEach((idx: number) => validatorIndexes.value.add(idx))
  }
}

</script>

<template>
  <div>
    <BCard no-body>
      <BTabs card>
        <BTab title="By Index">
          <form @submit.prevent="parseValidatorIndexes">
            <input
                v-model="indexesInput"
                required
                type="text"
                pattern="^( *(?:\d+) *,? *)*$"
                oninvalid="this.setCustomValidity('A validator index should be a positive number')"
                oninput="this.setCustomValidity('')"
                class="form-control"
                placeholder="Type your validator index(es) here, separated by commas"
            >
            <div class="d-flex align-items-center m-2">
              <BButton variant="primary" class="m-2" type="submit">Add</BButton>
              <div v-if="validatorIndexes.size > 0" class="d-flex align-items-center">
                <BButton v-if="validatorIndexes.size > 0" @click="validatorIndexes.clear()" class="m-2">Reset</BButton>
                <p class="my-1">Validator{{ validatorIndexes.size > 1 ? "s" : "" }}: {{ validatorIndexes.size <= 10 ? `${Array.from(validatorIndexes).sort((a, b) => a - b).join(", ")}` : `${Array.from(validatorIndexes).sort((a, b) => a - b).slice(0, 10).join(", ")}, ... [${validatorIndexes.size}]` }}</p>
              </div>
            </div>
          </form>
        </BTab>
        <BTab title="By Public Key">
          <form @submit.prevent="getIndexesForPubkeys">
            <input
                v-model="pubkeysInput"
                required
                type="text"
                pattern="^( *(?:0x[a-fA-F0-9]{96}) *,? *)*$"
                oninvalid="this.setCustomValidity('A public key should begin with 0x and be 98 characters long')"
                oninput="this.setCustomValidity('')"
                class="form-control"
                placeholder="Type your validator public key(s) here, separated by commas"
            >
            <div class="d-flex align-items-center m-2">
              <BButton variant="primary" class="m-2" type="submit">Add</BButton>
              <div v-if="validatorIndexes.size > 0" class="d-flex align-items-center">
                <BButton v-if="validatorIndexes.size > 0" @click="validatorIndexes.clear()" class="m-2">Reset</BButton>
                <p class="my-1">Validator{{ validatorIndexes.size > 1 ? "s" : "" }}: {{ validatorIndexes.size <= 10 ? `${Array.from(validatorIndexes).sort((a, b) => a - b).join(", ")}` : `${Array.from(validatorIndexes).sort((a, b) => a - b).slice(0, 10).join(", ")}, ... [${validatorIndexes.size}]` }}</p>
              </div>
            </div>
          </form>
        </BTab>
        <BTab title="By Deposit Address">
          <form @submit.prevent="getIndexesForDepositAddresses">
            <input
                v-model="depositAddressesInput"
                required
                type="text"
                pattern="^(\s*(?:0x[a-fA-F0-9]{40})\s*,?\s*)+$"
                oninvalid="this.setCustomValidity('A deposit address should begin with 0x and be 42 characters long')"
                oninput="this.setCustomValidity('')"
                class="form-control"
                placeholder="Type your deposit address(es) here, separated by commas"
            >
            <div class="d-flex align-items-center m-2">
              <BButton variant="primary" class="m-2" type="submit">Add</BButton>
              <div v-if="validatorIndexes.size > 0" class="d-flex align-items-center">
                <BButton v-if="validatorIndexes.size > 0" @click="validatorIndexes.clear()" class="m-2">Reset</BButton>
                <p class="my-1">Validator{{ validatorIndexes.size > 1 ? "s" : "" }}: {{ validatorIndexes.size <= 10 ? `${Array.from(validatorIndexes).sort((a, b) => a - b).join(", ")}` : `${Array.from(validatorIndexes).sort((a, b) => a - b).slice(0, 10).join(", ")}, ... [${validatorIndexes.size}]` }}</p>
              </div>
            </div>
          </form>
        </BTab>
      </BTabs>
    </BCard>
  </div>
  <div v-if="validatorIndexes.size > 0" class="d-flex flex-row align-items-center">
  </div>
</template>

<style scoped>
input:valid {
  border-color: rgb(var(--serenita-blue-dark));
}
input:invalid {
  border-color: red;
}
</style>
