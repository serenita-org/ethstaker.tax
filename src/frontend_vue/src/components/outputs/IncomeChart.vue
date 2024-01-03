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
    <BButtonGroup>
      <BButton @click="showIncomeInFiat = !showIncomeInFiat" variant="secondary">Show income in {{ showIncomeInFiat ? "ETH" : currency }}</BButton>
      <BButton @click="Chart.getChart(chartCanvasId)?.resetZoom()" class="ms-1" variant="outline-secondary">Reset zoom</BButton>
    </BButtonGroup>
  </div>
</template>



<script lang="ts">
import { PropType } from "vue";
import Chart, {TooltipItem} from "chart.js/auto";
import { ChartConfiguration } from "chart.js";
import zoomPlugin from 'chartjs-plugin-zoom';
import 'chartjs-adapter-date-fns';
import {CHART_COLORS, gweiToEthMultiplier, WeiToGweiMultiplier} from "../../constants.ts";
import {PricesResponse, RewardForDate, RocketPoolValidatorRewards, ValidatorRewards} from "../../types/rewards.ts";
import {getOperatorReward, isRocketPoolValidatorRewards} from "../../functions/rocketpool.ts";

Chart.register(zoomPlugin);

// Each canvas needs to have a unique ID
let uid = 0;

export default {
  props: {
    rewardsData: {
      type: Object as PropType<(ValidatorRewards | RocketPoolValidatorRewards)[]>,
      required: true,
    },
    priceDataEth: {
      type: Object as PropType<PricesResponse>,
      required: true,
    },
    currency: {
      type: String,
      required: true
    },
    useConsensusIncomeOnWithdrawal: {
      type: Boolean,
      required: true,
    },
    useRocketPoolMode: {
      type: Boolean,
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
      showIncomeInFiat: false,
      chartCanvasId: `simpleBarChartCanvas-${uid}`,
      backgroundColor: CHART_COLORS,
      Chart,
    };
  },
  watch: {
    rewardsData() {
      this.updateData();
    },
    useConsensusIncomeOnWithdrawal() {
      this.updateData();
    },
    useRocketPoolMode() {
      this.updateData();
    },
    showIncomeInFiat() {
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

      const allDatesSet : Set<string> = new Set();
      this.rewardsData.forEach(validatorRewards => {
        if (this.useConsensusIncomeOnWithdrawal) {
          validatorRewards.withdrawals.forEach(reward => allDatesSet.add(reward.date));
        } else {
          validatorRewards.consensus_layer_rewards.forEach(reward => allDatesSet.add(reward.date));
        }
        validatorRewards.execution_layer_rewards.forEach(reward => allDatesSet.add(reward.date));
      });
      const allDates = Array.from(allDatesSet).sort();

      // Prepare data for the chart
      const consensusLayerData = allDates.map(date => {
          const rewardsTotal = this.rewardsData.reduce((total, validatorData) => {
              const isRocketPoolValidator = isRocketPoolValidatorRewards(validatorData);

              let matchingReward: RewardForDate;
              if (this.useConsensusIncomeOnWithdrawal) {
                matchingReward = validatorData.withdrawals.find(reward => reward.date === date) ?? { amount_wei: 0n, date: date};
              } else {
                matchingReward = validatorData.consensus_layer_rewards.find(reward => reward.date === date) ?? { amount_wei: 0n, date: date};
              }

              if (isRocketPoolValidator && this.useRocketPoolMode) {
                matchingReward = getOperatorReward(
                    (validatorData as RocketPoolValidatorRewards).bonds,
                    (validatorData as RocketPoolValidatorRewards).fees,
                    matchingReward
                );
              }

              return total + (matchingReward ? matchingReward.amount_wei : BigInt(0));
          }, BigInt(0));
          const totalGwei = rewardsTotal / WeiToGweiMultiplier;
          if (totalGwei > Number.MAX_SAFE_INTEGER) throw `totalGwei (${totalGwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
          const totalEth = Number(totalGwei) / Number(gweiToEthMultiplier);
          const priceDataForDate = this.priceDataEth.prices.find(data => data.date == date);
          if (!priceDataForDate) throw `No price data for ${date}!`
          return [totalEth, priceDataForDate.price * totalEth];
      });

      const executionLayerData = allDates.map(date => {
          const rewardsTotal = this.rewardsData.reduce((total, validatorData) => {
              const isRocketPoolValidator = isRocketPoolValidatorRewards(validatorData);

              let matchingReward = validatorData.execution_layer_rewards.find(reward => reward.date === date) ?? { amount_wei: 0n, date: date};

              if (isRocketPoolValidator && this.useRocketPoolMode) {
                matchingReward = getOperatorReward(
                    (validatorData as RocketPoolValidatorRewards).bonds,
                    (validatorData as RocketPoolValidatorRewards).fees,
                    matchingReward
                );
              }

              return total + (matchingReward ? matchingReward.amount_wei : BigInt(0));
          }, BigInt(0));
          const totalGwei = rewardsTotal / WeiToGweiMultiplier;
          if (totalGwei > Number.MAX_SAFE_INTEGER) throw `totalGwei (${totalGwei}) > Number.MAX_SAFE_INTEGER (${Number.MAX_SAFE_INTEGER})`
          const totalEth = Number(totalGwei) / Number(gweiToEthMultiplier);
          const priceDataForDate = this.priceDataEth.prices.find(data => data.date == date);
          if (!priceDataForDate) throw `No price data for ${date}!`
          return [totalEth, priceDataForDate.price * totalEth];
      });

      chart.data = {
        labels: allDates,
        datasets: [
          {
            label: `Consensus Layer Income [${this.showIncomeInFiat ? this.currency : "ETH"}]`,
            data: this.showIncomeInFiat ? consensusLayerData.map(d => d[1]) : consensusLayerData.map(d => d[0] as number),
            backgroundColor: CHART_COLORS[0],
            type: 'bar',
          },
          {
            label: `Execution Layer Income [${this.showIncomeInFiat ? this.currency : "ETH"}]`,
            data: this.showIncomeInFiat ? executionLayerData.map(d => d[1]) : executionLayerData.map(d => d[0] as number),
            backgroundColor: CHART_COLORS[6],
            type: 'bar',
          },
        ]
      };

      chart.options.scales = {
        x: {
          stacked: true,
          type: 'time',
          time: {
            tooltipFormat: 'PP'
          }
        },
        y: {
          title: {
            display: true,
            text: this.showIncomeInFiat ? `Income [${this.currency}]` : "Income [ETH]",
          },
          stacked: true,
        },
      }

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
                      return `Total: ${total.toFixed(this.showIncomeInFiat ? 2 : 5)} ${this.showIncomeInFiat ? this.currency : "ETH"}`;
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
