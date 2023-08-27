<template>
  <div
    ref="chartContainer"
    class="chart-container"
    :style="{
      margin: 'auto',
      height: chartContainerHeight,
      width: chartContainerWidth,
    }"
  >
    <canvas :id="chartCanvasId"></canvas>
  </div>
</template>



<script lang="ts">
import { PropType } from "vue";
import Chart from "chart.js/auto";
import { ChartConfiguration } from "chart.js";
import {CHART_COLORS, gweiToEthMultiplier, WeiToEthMultiplier, WeiToGweiMultiplier} from "../../constants.ts";
import {ValidatorRewards} from "../../types/rewards.ts";

// Each canvas needs to have a unique ID
let uid = 0;

export default {
  props: {
    rewardsData: {
      type: Object as PropType<ValidatorRewards[]>,
      required: true,
    },
    chartContainerHeight: {
      type: String,
      required: false,
      default: "200px",
    },
    chartContainerWidth: {
      type: String,
      required: false,
      default: "100vw",
    },
  },
  data() {
    uid += 1;
    return {
      chartCanvasId: `simpleBarChartCanvas-${uid}`,
      backgroundColor: CHART_COLORS,
    };
  },
  watch: {
    rewardsData() {
      this.updateData();
    },
  },
  async mounted() {
    this.setUpChart();
    this.updateData();
  },
  async beforeUnmount() {
    this.destroyChart();
  },
  methods: {
    updateData() {
      const chart = Chart.getChart(this.chartCanvasId);
      if (!chart) {
        return;
      }

      const allDatesSet = new Set();
      this.rewardsData.forEach(validatorRewards => {
          validatorRewards.consensus_layer_rewards.forEach(reward => allDatesSet.add(reward.date));
          validatorRewards.execution_layer_rewards.forEach(reward => allDatesSet.add(reward.date));
      });
      const allDates = Array.from(allDatesSet).sort((a, b) => a - b);

      // Prepare data for the chart
      const consensusLayerData = allDates.map(date => {
          const rewardsTotal = this.rewardsData.reduce((total, response) => {
              const matchingReward = response.consensus_layer_rewards.find(reward => reward.date === date);
              return total + (matchingReward ? matchingReward.amount_wei : BigInt(0));
          }, BigInt(0));
          const totalGwei = rewardsTotal / WeiToGweiMultiplier;
          if (totalGwei > Number.MAX_SAFE_INTEGER) throw `totalGwei (${totalGwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
          return Number(totalGwei) / Number(gweiToEthMultiplier);
      });

      const executionLayerData = allDates.map(date => {
          const rewardsTotal = this.rewardsData.reduce((total, response) => {
              const matchingReward = response.execution_layer_rewards.find(reward => reward.date === date);
              return total + (matchingReward ? matchingReward.amount_wei : BigInt(0));
          }, BigInt(0));
          const totalGwei = rewardsTotal / WeiToGweiMultiplier;
          if (totalGwei > Number.MAX_SAFE_INTEGER) throw `totalGwei (${totalGwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
          return Number(totalGwei) / Number(gweiToEthMultiplier);
      });

      chart.data = {
        labels: allDates,
        datasets: [
          {
            label: 'Consensus Layer Income',
            data: consensusLayerData,
            backgroundColor: CHART_COLORS[0],
          },
          {
            label: 'Execution Layer Income',
            data: executionLayerData,
            backgroundColor: CHART_COLORS[6],
          }
        ]
      };
      chart.update();
    },
    setUpChart() {
      const config: ChartConfiguration = {
        type: "bar",
        data: null,
        options: {
          maintainAspectRatio: false,
          scales: {
            x: {
              stacked: true,
            },
            y: {
              stacked: true,
            },
          },
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              displayColors: false,
            },
          },
        },
      };

      new Chart(this.chartCanvasId, config);
    },
    destroyChart() {
      const chart = Chart.getChart(this.chartCanvasId);
      if (!chart) {
        return;
      }

      chart.update("hide");
    },
  },
};
</script>
