import Chart, { TooltipItem } from 'chart.js/auto';
import 'chartjs-adapter-moment';

const CHART_ELEMENT_ID = "rewardsChartCanvas";

export interface RewardsDailyChartData {
    date: string;
    consensusLayerIncome: number;
    executionLayerIncome: number;
}

export function clearChart() {
    let existingChart = Chart.getChart(CHART_ELEMENT_ID); // <canvas> id
    if (existingChart !== undefined) {
      existingChart.destroy();
    }
}

export function populateChart(data: RewardsDailyChartData[]) {
    clearChart();

    const canvasHtmlElement = document.getElementById(CHART_ELEMENT_ID) as HTMLCanvasElement;

    // There may be multiple entries for the same date - consolidate them and round them - no need for superhigh precision
    // in the chart
    let combinedDailyData = [];
    let uniqueDates = data.map(item => item.date).filter((value, idx, self) => self.indexOf(value) === idx);
    for (let date of uniqueDates) {
        let consensusLayerIncome = data.filter(
            (item) => item.date === date)
            .map(
                item => item.consensusLayerIncome
            )
            .reduce(
                (total, incomeForValidator) => incomeForValidator + total, 0
            );
        consensusLayerIncome = parseFloat(consensusLayerIncome.toFixed(6));
        let executionLayerIncome = data.filter(
            (item) => item.date === date)
            .map(
                item => item.executionLayerIncome
            )
            .reduce(
                (total, incomeForValidator) => incomeForValidator + total, 0
            );
        executionLayerIncome = parseFloat(executionLayerIncome.toFixed(6));
        combinedDailyData.push({
            date: date,
            consensusLayerIncome: consensusLayerIncome,
            executionLayerIncome: executionLayerIncome,
        });
    }

    new Chart(
        canvasHtmlElement,
        {
          type: 'bar',
          data: {
            labels: combinedDailyData.map(item => item.date),
            datasets: [
              {
                label: 'Consensus Layer Income',
                data: combinedDailyData.map(item => item.consensusLayerIncome),
              },
              {
                label: 'Execution Layer Income',
                data: combinedDailyData.map(item => item.executionLayerIncome)
              },
            ]
          },
          options: {
            plugins: {
              tooltip: {
                displayColors: false,
                callbacks: {
                  label: function(tooltipItem: TooltipItem<"bar">) {
                    let labels = [];
                    for (const dataset of tooltipItem.chart.data.datasets) {
                        const datasetValue = dataset.data[tooltipItem.dataIndex];
                        labels.push(dataset.label + ": " + datasetValue + " Ξ");
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
                      return 'Total: ' + total + " Ξ";
                  }
                }
              }
            },
            scales: {
              x: {
                type: "time",
                stacked: true,
              },
              y: {
                title: {
                  display: true,
                  text: "Income [ETH]"
                },
                stacked: true,
              }
            },
          }
        }
    );
}
