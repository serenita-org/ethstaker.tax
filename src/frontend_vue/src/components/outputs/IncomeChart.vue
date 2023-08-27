<template>
  <div class="d-flex flex-column align-items-center">
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
    <BButton class="w-25" @click="Chart.getChart(chartCanvasId)?.resetZoom()">Reset zoom</BButton>
  </div>
</template>



<script lang="ts">
import { PropType } from "vue";
import Chart, {TooltipItem} from "chart.js/auto";
import { ChartConfiguration } from "chart.js";
import zoomPlugin from 'chartjs-plugin-zoom';
import 'chartjs-adapter-date-fns';
import {CHART_COLORS, gweiToEthMultiplier, WeiToGweiMultiplier} from "../../constants.ts";
import {ValidatorRewards} from "../../types/rewards.ts";

Chart.register(zoomPlugin);

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
      Chart,
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
      const allDates = Array.from(allDatesSet).sort();

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
        data: {
          labels: [],
          datasets: []
        },
        options: {
          maintainAspectRatio: false,
          scales: {
            x: {
              stacked: true,
              type: 'time',
              time: {
                tooltipFormat: 'PP'
              }
            },
            y: {
              stacked: true,
            },
          },
          plugins: {
            zoom: {
              zoom: {
                drag: {
                  enabled: true
                },
                pinch: {
                  enabled: true
                },
                mode: 'x',
              }
            },
            legend: {
              display: true,
            },
            tooltip: {
              displayColors: false,
              callbacks: {
                  label: function(tooltipItem: TooltipItem<"bar">) {
                    let labels = [];
                    for (const dataset of tooltipItem.chart.data.datasets) {
                        const datasetValue = dataset.data[tooltipItem.dataIndex];
                        labels.push(dataset.label + ": " + (datasetValue as number).toFixed(5));
                    }
                    return labels;
                  },
                  footer: (context) => {
                      let total = 0;
                      for (let ctx of context) {
                        for (const dataset of ctx.chart.data.datasets) {
                          total += dataset.data[ctx.dataIndex] as number;
                        }
                      }
                      return 'Total: ' + total.toFixed(5) + " Ether";
                  }
                }
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
