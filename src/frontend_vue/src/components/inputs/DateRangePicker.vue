<script setup lang="ts">

import {onMounted, ref, watch} from "vue";

const startDateString = ref("2024-01-01");
const endDateString = ref("2024-12-31");


const emit = defineEmits(['date-range-changed']);
onMounted(() => {
  emit('date-range-changed', startDateString.value, endDateString.value);
})

watch(startDateString, async () => {
  emit('date-range-changed', startDateString.value, endDateString.value);
})
watch(endDateString, async () => {
  emit('date-range-changed', startDateString.value, endDateString.value);
})


</script>

<template>
  <div class="input-group">
    <label class="input-group-text" for="startDate">From</label>
    <input v-model="startDateString" id="startDate" type="date" class="form-control">
    <label class="input-group-text" for="endDate">To</label>
    <input v-model="endDateString" id="endDate" type="date" class="form-control">
  </div>
</template>
