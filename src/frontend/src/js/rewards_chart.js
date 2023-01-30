import Chart from 'chart.js/auto';
import 'chartjs-adapter-moment';

const CHART_ELEMENT_ID = "rewardsChartCanvas";

export function clearChart(data) {
    let existingChart = Chart.getChart(CHART_ELEMENT_ID); // <canvas> id
    if (existingChart !== undefined) {
      existingChart.destroy();
    }
}

export function populateChart(data) {
    clearChart();

    const canvasHtmlElement = document.getElementById(CHART_ELEMENT_ID);

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
        consensusLayerIncome = consensusLayerIncome.toFixed(6);
        let executionLayerIncome = data.filter(
            (item) => item.date === date)
            .map(
                item => item.executionLayerIncome
            )
            .reduce(
                (total, incomeForValidator) => incomeForValidator + total, 0
            );
        executionLayerIncome = executionLayerIncome.toFixed(6);
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
                label: 'Consensus Income',
                data: combinedDailyData.map(item => item.consensusLayerIncome),
              },
              {
                label: 'Execution Income',
                data: combinedDailyData.map(item => item.executionLayerIncome)
              },
            ]
          },
          options: {
            plugins: {
              tooltip: {
                callbacks: {
                  footer: (context) => {
                      let total = 0;
                      for (let ctx of context) {
                        for (let dataset of ctx.chart.data.datasets) {
                          total += Number(dataset.data[ctx.dataIndex]);
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
            tooltips: {
                mode: 'label',
                callbacks: {
                    label: function(tooltipItem, data) {
                        const datasetLabel = data.datasets[tooltipItem.datasetIndex].label;
                        const tooltipItemValue = data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index];

                        let total = 0;
                        for (let i = 0; i < data.datasets.length; i++)
                            total += data.datasets[i].data[tooltipItem.index];
                        if (tooltipItem.datasetIndex !== data.datasets.length - 1) {
                            return datasetLabel + " : $" + tooltipItemValue.toFixed(2).replace(/(\d)(?=(\d{3})+\.)/g, '$1,');
                        } else {
                            return [datasetLabel + " : $" + tooltipItemValue.toFixed(2).replace(/(\d)(?=(\d{3})+\.)/g, '$1,'), "Total : $" + total];
                        }
                    }
                }
            },
          }
        }
    );
}
