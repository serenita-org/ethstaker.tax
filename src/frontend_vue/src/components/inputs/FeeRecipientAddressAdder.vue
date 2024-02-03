<script setup lang="ts">
import {onBeforeUnmount, ref, Ref, watch} from "vue";

let expectedFeeRecipientAddressesInput: Ref<string> = ref("");

const emit = defineEmits<{
  (e: 'fee-recipient-addresses-changed', addresses: Set<string>): void
}>()

watch(expectedFeeRecipientAddressesInput, async () => {
  emit('fee-recipient-addresses-changed', new Set(expectedFeeRecipientAddressesInput.value.split(",").map(function(item) {
    return item.trim();
  })));
})

onBeforeUnmount(() => {
  // Reset addresses when component unmounts
  emit('fee-recipient-addresses-changed', new Set([]));
})

</script>

<template>
  <h3>Add your fee recipient addresses</h3>
  <p>(optional but recommended in order to verify execution layer rewards)</p>
  <form @submit.prevent>
    <input
      v-model.lazy="expectedFeeRecipientAddressesInput"
      type="text"
      oninvalid="this.setCustomValidity('A fee recipient address should begin with 0x and be 42 characters long')"
      oninput="this.setCustomValidity('')"
      pattern="^(\s*(?:0x[a-fA-F0-9]{40})\s*,?\s*)+$"
      class="form-control"
      placeholder="Type your fee recipient address(es) here, separated by commas"
    />
  </form>
</template>
