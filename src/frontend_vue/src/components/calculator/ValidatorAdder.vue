<script setup lang="ts">
import { ref, watch } from 'vue'
import axios from "axios";


const pubKeyUrl = new URL("https://ethstaker.tax/api/v1/index_for_publickey", window.location.href);
const depositAddrUrl = new URL("https://ethstaker.tax/api/v1/indexes_for_eth1_address", window.location.href);


//const indexesInput = ref("1, 2, 3");
const indexesInput = ref("12, 13, 32");
const pubkeysInput = ref("0xa9df2cfd79a8b569e7abc286047ade81dbc2e5b89bfd8c00b0913ba3c539b80ff469e77465c6d1815b29e151ab8efd38, 0x94c918316fb3db0e10feb4ee9d526d8bf991658bd5f68303ecef17e41482fec4362595f322408925b74719cd57c011c6");
//const pubkeysInput = ref("");
const depositAddressesInput = ref("0x16ab90Dd40DEE049F5afdC40A0B1FD083EA8e534");
//const depositAddressesInput = ref("");

const validatorIndexes = ref(new Set());

const emit = defineEmits(['validatorsChanged']);

watch(validatorIndexes.value, async (newValidatorIndexes) => {
  emit('validatorsChanged', newValidatorIndexes);
})


function parseValidatorIndexes(event) {
  const inputIndexes = indexesInput.value.split(",").filter(Number).map(function(item) {
    return parseInt(item.trim());
  });
  inputIndexes.forEach(value => {
    validatorIndexes.value.add(value)
  });
}


async function getIndexesForPubkeys(event) {
  const inputPubkeys = pubkeysInput.value.split(",").map(function(item) {
    return item.trim();
  });

  for (const pubkey of [...new Set(inputPubkeys)]) {
    const resp = await axios.get(pubKeyUrl.toString(), { params: {
      publickey: pubkey
    }});

    if (resp.status !== 200) {
      const errorMessage = `Unable to get indexes for pubkey ${pubkey}!`;
      alert(errorMessage);
      throw errorMessage;
    }
    validatorIndexes.value.add(resp.data);
  }
}

async function getIndexesForDepositAddresses(event) {
  const inputDepositAddresses = depositAddressesInput.value.split(",").map(function(item) {
    return item.trim();
  });

  for (const depositAddress of [...new Set(inputDepositAddresses)]) {
    const resp = await axios.get(depositAddrUrl.toString(), { params: {
      eth1_address: depositAddress
    }});

    if (resp.status !== 200) {
      const errorMessage = `Unable to get indexes for deposit address ${depositAddress}!`;
      alert(errorMessage);
      throw errorMessage;
    }
    resp.data.forEach(idx => validatorIndexes.value.add(idx))
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
            <BButton variant="primary" class="mt-2" type="submit">Add</BButton>
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
            <BButton variant="primary" class="mt-2" type="submit">Add</BButton>
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
            <BButton variant="primary" class="mt-2" type="submit">Add</BButton>
          </form>
        </BTab>
      </BTabs>
    </BCard>
  </div>
  <div v-if="validatorIndexes.size > 0">
    <p class="my-1">Total validators: {{ validatorIndexes.size }} ( {{ Array.from(validatorIndexes).sort((a, b) => a - b).toString() }} )</p>
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
