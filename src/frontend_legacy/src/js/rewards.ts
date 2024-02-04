import { clearChart, populateChart, RewardsDailyChartData } from "./rewards_chart";
import Pikaday from "pikaday";
import _ from "lodash";

import { AggregateRewards } from "./schema";

let AGGREGATE_REWARDS_DATA: AggregateRewards;


function handleErrorMessage(errorMessage: string, error: Error | null) {
    if (errorMessage.toString().indexOf("Too Many Requests") > -1) {
        errorMessage = "You have been rate limited, please try again later.";
    } else {
        errorMessage = "An error occurred, please try again. If the issue persists, check the browser console for more information.";
    }
    showErrorMessage(errorMessage);
    console.error('An error occurred:', error);
}

async function requestWithErrorHandling(url: string) {
    const response = await fetch(url);
    const { status } = response;

    if (status !== 200) {
        handleErrorMessage(await response.text(), null);
    }

    try {
        return await response.json();
    } catch(err) {
        handleErrorMessage(err.message, err);
        throw err;
    }
}

function addInputElement(event: Event) {
    const clickedElement = event.target as HTMLElement;
    const inputGroup = clickedElement.parentElement as HTMLElement;
    const inputGroupContainer = inputGroup.parentElement as HTMLElement;
    const newInputGroup = inputGroup.cloneNode(true) as HTMLElement;

    // Set value to empty for cloned input element
    const newInputElement = newInputGroup.children[0] as HTMLInputElement;
    newInputElement.value = "";

    // Add event listener for "Add more" button
    const newInputGroupAddAnotherBtn = newInputGroup.children[1];
    newInputGroupAddAnotherBtn.addEventListener("click", addInputElement);

    // Add a remove button to the new input group if there is no remove button present
    let removeButton;
    if (newInputGroup.children.length === 2) {
        removeButton = document.createElement("button");
        removeButton.className = "btn btn-outline-secondary";
        removeButton.setAttribute("type", "button");
        removeButton.innerHTML = "<i class='bi-dash-circle'></i> Remove";
        newInputGroup.appendChild(removeButton);
    } else {
        removeButton = newInputGroup.children[2];
    }
    removeButton.addEventListener("click", () => newInputGroup.remove());

    // Add the new input group to the parent input group container
    inputGroupContainer.appendChild(newInputGroup);

    // Focus on the new input element - so the user doesn't have to
    // select it to continue typing
    newInputElement.focus();
}

function showCustomDateRangeInput(show: Boolean) {
    const element = document.getElementById("customDateRangeInput");
    if (show) {
        element.classList.remove("d-none");
    } else {
        element.classList.add("d-none");
    }
}

function selectDateRangeByYear() {
    const selectDateRangeElement = document.getElementById("selectDateRange") as HTMLSelectElement;

    // Toggle datepicker visibility depending on selected date range
    if (selectDateRangeElement.value === "custom") {
        // Selected custom date, show datepickers
        showCustomDateRangeInput(true);

        // Init Pikaday date pickers
        const datePickerIds = ["datePickerStart", "datePickerEnd"];
        datePickerIds.forEach((elementId) => {
            new Pikaday({
                field: document.getElementById(elementId),
                format: "YYYY-MM-DD"
            });
        });
    } else if (selectDateRangeElement.value === "since_genesis") {
        // Selected since genesis as the date, hide datepickers
        showCustomDateRangeInput(false);

        const startDatePicker = document.getElementById("datePickerStart") as HTMLInputElement;
        // Genesis was Dec 12th 12PM UTC, which may have still been November 30th in some timezones
        startDatePicker.value = "2020-11-30";

        const endDatePicker = document.getElementById("datePickerEnd") as HTMLInputElement;
        // toISOString first converts to UTC - handle that by adding the timezone offset
        let endDate = new Date();
        const offset = endDate.getTimezoneOffset();
        endDate = new Date(endDate.getTime() - (offset*60*1000));
        endDatePicker.value = endDate.toISOString().split('T')[0];
    } else {
        // Selected a year as a date, hide datepickers
        showCustomDateRangeInput(false);

        const startDatePicker = document.getElementById("datePickerStart") as HTMLInputElement;
        startDatePicker.value = selectDateRangeElement.value  + "-01-01";

        const endDatePicker = document.getElementById("datePickerEnd") as HTMLInputElement;
        endDatePicker.value = selectDateRangeElement.value  + "-12-31";
    }
}

window.addEventListener("load", () => {
    const selectDateRangeElement = document.getElementById("selectDateRange");
    selectDateRangeElement.addEventListener("change", selectDateRangeByYear);
    showCustomDateRangeInput(false);
    selectDateRangeByYear();
})

function cleanupFromPreviousRequest() {
    // Hide container that contains all previously retrieved rewards data
    document.getElementById("allRewardsDataContainer").classList.add("d-none");

    AGGREGATE_REWARDS_DATA = null;

    const rewardsTablesContainer = document.getElementById("rewardsTablesContainer");
    // Remove children elements
    while (rewardsTablesContainer.firstChild) {
        rewardsTablesContainer.firstChild.remove()
    }

    const sumRewardsTablesContainer = document.getElementById("sumRewardsTablesContainer");
    // Remove children tables
    while (sumRewardsTablesContainer.firstChild) {
        sumRewardsTablesContainer.firstChild.remove()
    }

    // Collapse
    const rewardsTablesCollapse = document.getElementById("rewardsTablesCollapse");
    rewardsTablesCollapse.classList.remove("show");

    // Hide error message
    document.getElementById("calculateErrorMessage").classList.add("d-none");

    // Clear chart
    clearChart();
}

function toggleCalculateButton(enabled: Boolean) {
    (document.getElementById("calculateButton") as HTMLButtonElement).disabled = !enabled;
}

function toggleCalculateMessage(show: Boolean) {
    if (show) {
        document.getElementById("calculateInfoMessage").classList.remove("d-none");
    }
    else {
        document.getElementById("calculateInfoMessage").classList.add("d-none");
    }
}

function showErrorMessage(message: string) {
    document.getElementById("calculateErrorMessage").classList.remove("d-none");
    document.getElementById("calculateErrorMessage").innerText = message;
    toggleCalculateButton(true);
    toggleCalculateMessage(false);
}


function getRewardsForValidatorIndexes(validatorIndexes: number[]) {
    const params = new URLSearchParams();

    if (validatorIndexes.length == 0) {
        alert("No validators found for your inputs!");
        showErrorMessage("No validators found for your inputs!");
        return;
    }

    validatorIndexes.forEach((validatorIndex) => {
        params.append("validator_indexes", validatorIndex.toString());
    })

    params.append("start_date", (document.getElementById("datePickerStart") as HTMLInputElement).value)
    params.append("end_date", (document.getElementById("datePickerEnd") as HTMLInputElement).value)

    params.append("timezone", "UTC")

    params.append("currency", (document.getElementById("selectCurrency") as HTMLSelectElement).value)

    const url = new URL("/api/v1/rewards", window.location.href)
    url.search = params.toString();

    requestWithErrorHandling(url.href)
        .then((data: AggregateRewards) => {
            AGGREGATE_REWARDS_DATA = data;

            // Sum total rewards over all validators
            let sumConsensusIncomeEth = 0;
            let sumConsensusIncomeCurr = 0;
            let sumExecutionIncomeEth = 0;
            let sumExecutionIncomeCurr = 0;
            let currency;
            const sumRewardsTablesContainer = document.getElementById("sumRewardsTablesContainer");

            // Add a summary table for the total income over all validators
            const sumTotalTable = document.createElement("table");
            sumTotalTable.classList.add("table");
            sumTotalTable.classList.add("text-center");
            sumRewardsTablesContainer.appendChild(sumTotalTable);

            // Add action buttons container
            const actionButtonsDiv = document.createElement("div");
            actionButtonsDiv.classList.add("text-center");
            sumRewardsTablesContainer.appendChild(actionButtonsDiv);

            // Add a button to download a combined CSV export of the rewards
            let exportCombinedDiv = document.createElement("div");
            actionButtonsDiv.appendChild(exportCombinedDiv);

            let btn = document.createElement("button");
            btn.classList.add("btn");
            btn.classList.add("btn-primary");
            btn.classList.add("m-3");
            btn.innerHTML = "<i class=\"bi-cloud-download\"></i> Download CSV of daily rewards for all validators";
            btn.addEventListener("click", () => downloadRewardsDataAsCsv(null));
            exportCombinedDiv.appendChild(btn);

            // Add the option to group combined rewards by date
            let groupByDateCheckBox = document.createElement("input");
            groupByDateCheckBox.type = "checkbox";
            groupByDateCheckBox.classList.add("m-3");
            groupByDateCheckBox.id = "groupByDateCheckBox";
            groupByDateCheckBox.value = "groupByDate";
            let groupByDateCheckBoxLabel = document.createElement("label");
            groupByDateCheckBoxLabel.innerText = "Group by date";
            exportCombinedDiv.appendChild(groupByDateCheckBox);
            exportCombinedDiv.appendChild(groupByDateCheckBoxLabel);

            // Add a button to expand the collapsed details
            btn = document.createElement("button");
            btn.classList.add("btn");
            btn.classList.add("btn-secondary");
            btn.classList.add("m-3");
            btn.type = "button"
            btn.setAttribute("data-bs-toggle", "collapse");
            btn.setAttribute("data-bs-target", "#rewardsTablesCollapse");
            btn.setAttribute("aria-controls", "rewardsTablesCollapse");
            btn.innerHTML = "<i class=\"bi-table\"></i> Show validator-specific details";
            actionButtonsDiv.appendChild(btn);

            currency = data.currency;
            let rewardTableColumnNames = [
                "Date",
                "Validator Index",
                "End-of-day validator balance [ETH]",
                "Consensus layer income [ETH]",
                "Execution layer income [ETH]",
                "Price [ETH/" + currency + "]",
                "Consensus layer income [" + currency + "]",
                "Execution layer income [" + currency + "]",
                "Withdrawals [ETH]"
            ];

            // Create a table for each validators' rewards
            const chartData: RewardsDailyChartData[] = [];
            const rewardsTablesContainer = document.getElementById("rewardsTablesContainer");
            data.validator_rewards.forEach(
                ({
                     eod_balances, initial_balance, validator_index,
                     exec_layer_block_rewards, withdrawals,
                     total_consensus_layer_eth, total_consensus_layer_currency,
                     total_execution_layer_eth, total_execution_layer_currency
                }) => {
                // Wrapper div
                const divElement = document.createElement("div");
                divElement.classList.add("m-3");

                // Table description
                const descriptionDivElement = document.createElement("div");
                descriptionDivElement.classList.add("d-inline");
                const paragraph = document.createElement("p");
                paragraph.classList.add("lead");
                paragraph.classList.add("d-inline");
                paragraph.innerText = "Rewards for validator index " + validator_index;
                descriptionDivElement.appendChild(paragraph);
                divElement.appendChild(descriptionDivElement);

                // CSV download button
                const btn = document.createElement("button");
                btn.classList.add("btn");
                btn.classList.add("btn-primary");
                btn.classList.add("m-3");
                btn.innerHTML = "<i class='bi-cloud-download'></i> CSV";
                btn.addEventListener("click", () => downloadRewardsDataAsCsv(validator_index));
                divElement.appendChild(btn);

                const tableElement = document.createElement("table");
                tableElement.id = "rewards_table_" + validator_index;
                tableElement.classList.add("table");

                // Table head
                const tableHead = document.createElement("thead");
                const headerRow = document.createElement("tr");

                rewardTableColumnNames.forEach((columnName) => {
                    if (columnName !== "Validator Index") {
                        const headerColumn = document.createElement("th");
                        headerColumn.innerText=columnName;
                        headerRow.appendChild(headerColumn);
                    }
                });

                tableHead.appendChild(headerRow);

                // Table body
                const tableBody = document.createElement("tbody");

                let prevBalance = 0;
                if (initial_balance !== null) {
                    prevBalance = initial_balance.balance;
                }
                eod_balances.forEach((balance) => {
                    const bodyRow = document.createElement("tr");

                    let dailyChartData = {} as RewardsDailyChartData;

                    // Date
                    dailyChartData["date"] = balance.date;
                    const dateColumn = document.createElement("th");
                    dateColumn.innerText = balance.date;
                    bodyRow.appendChild(dateColumn);

                    // End-of-day validator balance [ETH]
                    const eodValidatorBalanceColumn = document.createElement("th");
                    eodValidatorBalanceColumn.innerText = balance.balance.toFixed(6).toString();
                    bodyRow.appendChild(eodValidatorBalanceColumn);

                    // Consensus layer income [ETH] - account for withdrawals
                    let consensusIncEthForDate = balance.balance - prevBalance;
                    let withdrawalsForDate = 0;
                    withdrawals.filter(w => w.date == balance.date).forEach((w) => {
                        withdrawalsForDate += w.amount;
                    })
                    consensusIncEthForDate += withdrawalsForDate

                    dailyChartData["consensusLayerIncome"] = consensusIncEthForDate;
                    const consensusIncEthColumn = document.createElement("th");
                    consensusIncEthColumn.innerText = parseFloat(consensusIncEthForDate.toFixed(6)).toString();
                    bodyRow.appendChild(consensusIncEthColumn);

                    // // Execution layer income [ETH]
                    let execIncEthForDate = 0;
                    exec_layer_block_rewards.filter(br => br.date === balance.date).forEach((br) => {
                        execIncEthForDate += parseFloat(br.reward.toFixed(6));
                    })
                    dailyChartData["executionLayerIncome"] = execIncEthForDate;
                    const execIncEthColumn = document.createElement("th");
                    execIncEthColumn.innerText = execIncEthForDate.toString();
                    bodyRow.appendChild(execIncEthColumn);

                    // Price [ETH/currency]
                    const priceForDate = parseFloat(data.eth_prices[balance.date].toFixed(2));
                    const priceEthColumn = document.createElement("th");
                    priceEthColumn.innerText = priceForDate.toString()
                    bodyRow.appendChild(priceEthColumn);

                    // Consensus layer income [currency]
                    const consensusIncCurrForDate = parseFloat((priceForDate * consensusIncEthForDate).toFixed(6));
                    const consensusIncCurrColumn = document.createElement("th");
                    consensusIncCurrColumn.innerText = consensusIncCurrForDate.toString();
                    bodyRow.appendChild(consensusIncCurrColumn);

                    // // Execution layer income [currency]
                    const executionIncCurrForDate = parseFloat((priceForDate * execIncEthForDate).toFixed(6));
                    const executionIncCurrColumn = document.createElement("th");
                    executionIncCurrColumn.innerText = executionIncCurrForDate.toString();
                    bodyRow.appendChild(executionIncCurrColumn);

                    // Withdrawals [ETH]
                    const withdrawalsColumn = document.createElement("th");
                    withdrawalsColumn.innerText = parseFloat(withdrawalsForDate.toFixed(6)).toString();
                    bodyRow.appendChild(withdrawalsColumn);

                    prevBalance = parseFloat(balance.balance.toFixed(6));
                    tableBody.appendChild(bodyRow);

                    chartData.push(dailyChartData);
                });
                tableElement.appendChild(tableBody);

                // Table foot
                const tableFoot = document.createElement("tfoot");

                const footRow = document.createElement("tr");

                // Under Date column
                let footColumn;
                footColumn = document.createElement("td");
                footColumn.innerText="Total:";
                footRow.appendChild(footColumn);

                // Under End-of-day balance column
                footColumn = document.createElement("td");
                footRow.appendChild(footColumn);

                // Under consensus layer income [ETH] column
                footColumn = document.createElement("td");
                footColumn.innerText = total_consensus_layer_eth.toString();
                footRow.appendChild(footColumn);

                // Under exec layer income [ETH] column
                footColumn = document.createElement("td");
                footColumn.innerText = total_execution_layer_eth.toString();
                footRow.appendChild(footColumn);

                // Under price column
                footColumn = document.createElement("td");
                footRow.appendChild(footColumn);

                // Under consensus layer income [currency] column
                footColumn = document.createElement("td");
                footColumn.innerText = total_consensus_layer_currency.toString();
                footRow.appendChild(footColumn);

                // Under exec layer income [currency] column
                footColumn = document.createElement("td");
                footColumn.innerText = total_execution_layer_currency.toString();
                footRow.appendChild(footColumn);

                // Under withdrawals [ETH] column
                footColumn = document.createElement("td");
                let totalWithdrawals = 0;
                withdrawals.forEach((w) => {
                    totalWithdrawals += w.amount;
                })
                footColumn.innerText = parseFloat(totalWithdrawals.toFixed(6)).toString();
                footRow.appendChild(footColumn);

                tableFoot.appendChild(footRow);

                // Add all parts to the table
                tableElement.appendChild(tableHead);
                tableElement.appendChild(tableBody);
                tableElement.appendChild(tableFoot);

                divElement.appendChild(tableElement);

                rewardsTablesContainer.appendChild(divElement);

                sumConsensusIncomeEth += parseFloat(total_consensus_layer_eth.toFixed(6));
                sumConsensusIncomeCurr += parseFloat(total_consensus_layer_currency.toFixed(3));
                sumExecutionIncomeEth += parseFloat(total_execution_layer_eth.toFixed(6));
                sumExecutionIncomeCurr += parseFloat(total_execution_layer_currency.toFixed(3));
            })

            // Populate sum of total income table
            const tableHead = document.createElement("thead");
            const headerRow = document.createElement("tr");
            tableHead.appendChild(headerRow);

            let columnNames = [
                "",
                "ETH",
                currency,
            ];
            columnNames.forEach((columnName) => {
                const headerColumn = document.createElement("th");
                headerColumn.innerText = columnName;
                headerRow.appendChild(headerColumn);
            });
            sumTotalTable.appendChild(tableHead);

            const tableBody = document.createElement("tbody");

            let sumConsensusColumnValues = [
                "Consensus Layer Income",
                sumConsensusIncomeEth,
                sumConsensusIncomeCurr,
            ];
            const consensusBodyRow = document.createElement("tr");
            sumConsensusColumnValues.forEach((columnValue) => {
                const bodyColumn = document.createElement("td");
                bodyColumn.innerText = columnValue.toString();
                consensusBodyRow.appendChild(bodyColumn);
            })
            tableBody.appendChild(consensusBodyRow);

            let sumExecutionColumnValues = [
                "Execution Layer Income",
                sumExecutionIncomeEth,
                sumExecutionIncomeCurr,
            ];
            const executionBodyRow = document.createElement("tr");
            sumExecutionColumnValues.forEach((columnValue) => {
                const bodyColumn = document.createElement("td");
                bodyColumn.innerText = columnValue.toString();
                executionBodyRow.appendChild(bodyColumn);
            })
            tableBody.appendChild(executionBodyRow);

            let sumTotalColumnValues = [
                "Total Income",
                sumConsensusIncomeEth + sumExecutionIncomeEth,
                sumConsensusIncomeCurr + sumExecutionIncomeCurr,
            ];
            const totalBodyRow = document.createElement("tr");
            sumTotalColumnValues.forEach((columnValue) => {
                const bodyColumn = document.createElement("td");
                bodyColumn.innerText = columnValue.toString();
                totalBodyRow.appendChild(bodyColumn);
            })
            tableBody.appendChild(totalBodyRow);

            sumTotalTable.appendChild(tableBody);

            toggleCalculateButton(true);
            toggleCalculateMessage(false);

            // Populate rewards chart
            populateChart(chartData);

            // Show container that contains retrieved rewards data
            document.getElementById("allRewardsDataContainer").classList.remove("d-none");

            // Scroll to bottom to show resulting table
            window.scrollTo(0, document.body.scrollHeight);
        })
}

async function getRewards() {
    // Depending on the selected tab, it may be needed to fetch the
    // validator indexes first
    const tabElements = document.getElementById("validatorChoiceTab").children;
    let activeTab = null;
    for (let i = 0; i < tabElements.length; i++) {
        if (tabElements[i].children[0].className.includes("active")) {
            activeTab = tabElements[i].children[0];
        }
    }

    cleanupFromPreviousRequest();

    // Disable the calculate button to avoid users clicking it multiple times
    toggleCalculateButton(false);

    // Show message that it may take a while
    toggleCalculateMessage(true);

    if (activeTab.textContent === "Validator Indexes") {
        let validatorIndexes: number[] = Array();

        const indexInputGroups = document.getElementById("index").children as HTMLCollection;
        for (let i = 0; i < indexInputGroups.length; i++) {
            const indexInput = indexInputGroups[i].children[0] as HTMLInputElement;
            indexInput.value.split(",").forEach((value) => {
                if (value.length == 0) return;
                validatorIndexes.push(parseInt(value.trim()));
            })
        }
        getRewardsForValidatorIndexes(validatorIndexes);
    }
    else if (activeTab.textContent === "Validator public keys") {
        const pubKeyUrl = new URL("/api/v1/index_for_publickey", window.location.href);

        let pubKeyInputGroups = document.getElementById("pubkey").children;

        let indexRequests = Array();
        for (let i = 0; i < pubKeyInputGroups.length; i++) {
            const pubKeyInput = pubKeyInputGroups[i].children[0] as HTMLInputElement;

            pubKeyInput.value.split(",").forEach((value) => {
                if (value.length == 0) return;
                const pubKeyParams = new URLSearchParams();
                pubKeyParams.append("publickey", value.trim());
                pubKeyUrl.search = pubKeyParams.toString();
                indexRequests.push(requestWithErrorHandling(pubKeyUrl.href));
            })
        }
        let validatorIndexes = await Promise.all(indexRequests)
        getRewardsForValidatorIndexes(validatorIndexes);
    }
    else if (activeTab.textContent === "ETH1 deposit addresses") {
        const depositAddrUrl = new URL("/api/v1/indexes_for_eth1_address", window.location.href)

        let depositAddrInputGroups = document.getElementById("eth1").children;

        let indexRequests = Array();
        for (let i = 0; i < depositAddrInputGroups.length; i++) {
            const depositAddrInput = depositAddrInputGroups[i].children[0] as HTMLInputElement;

            depositAddrInput.value.split(",").forEach((value) => {
                if (value.length == 0) return;
                const depositAddrParams = new URLSearchParams();
                depositAddrParams.append("eth1_address", value.trim());
                depositAddrUrl.search = depositAddrParams.toString();
                indexRequests.push(requestWithErrorHandling(depositAddrUrl.href));
            })
        }
        let validatorIndexes = (await Promise.all(indexRequests) as Array<Array<number>>).flat();
        getRewardsForValidatorIndexes(validatorIndexes);
    } else {
        showErrorMessage("Invalid tab selected");
    }
}

interface CsvDataColumnValue {
    date: string,
    validatorIndex?: number,
    endOfDayBalance: number,
    consensusIncomeEth: number,
    executionIncomeEth: number,
    price: number,
    consensusIncomeCurr: number,
    executionIncomeCurr: number,
    withdrawalsEth: number,
}

function downloadRewardsDataAsCsv(validatorIndex: number | null, separator = ';') {
    let rewardsDataToDownload = AGGREGATE_REWARDS_DATA.validator_rewards;
    if (validatorIndex != null) {
        // Do not download all data, just for a specific validator
        rewardsDataToDownload = rewardsDataToDownload.filter((vr) => vr.validator_index === validatorIndex);
    }

    let csvRows = [];

    const groupByDate = (document.getElementById("groupByDateCheckBox") as HTMLInputElement).checked;
    const groupByDateSkipColumns = ["Validator Index"]

    let headerColumns = [
        "Date",
        "Validator Index",
        "End-of-day validator balance [ETH]",
        "Consensus layer income [ETH]",
        "Execution layer income [ETH]",
        "Price [ETH/" + AGGREGATE_REWARDS_DATA.currency + "]",
        "Consensus layer income [" + AGGREGATE_REWARDS_DATA.currency + "]",
        "Execution layer income [" + AGGREGATE_REWARDS_DATA.currency + "]",
        "Withdrawals [ETH]"
    ];

    if (groupByDate) {
        headerColumns = headerColumns.filter((columnName) => !groupByDateSkipColumns.includes(columnName));
    }

    csvRows.push(headerColumns.join(separator));

    let dataColumnValues: CsvDataColumnValue[] = [];
    for (let validatorRewards of rewardsDataToDownload) {
        let prevBalance = 0
        if (validatorRewards.initial_balance != null) {
            prevBalance = validatorRewards.initial_balance.balance;
        }
        validatorRewards.eod_balances.forEach((endOfDayBalance) => {
            // Consensus layer income - account for withdrawals
            let consensusIncEthForDate = endOfDayBalance.balance - prevBalance;
            let withdrawalsForDate = 0;
            validatorRewards.withdrawals.filter(w => w.date == endOfDayBalance.date).forEach((w) => {
                withdrawalsForDate += w.amount;
            })
            consensusIncEthForDate += withdrawalsForDate;

            // Execution layer income
            let execIncEthForDate = 0;
            validatorRewards.exec_layer_block_rewards.filter(br => br.date === endOfDayBalance.date).forEach((br) => {
                execIncEthForDate += br.reward;
            })

            // Price for date
            const price = parseFloat(AGGREGATE_REWARDS_DATA.eth_prices[endOfDayBalance.date].toFixed(3));

            dataColumnValues.push({
                date: endOfDayBalance.date,
                validatorIndex: validatorRewards.validator_index,
                endOfDayBalance: parseFloat(endOfDayBalance.balance.toFixed(6)),
                consensusIncomeEth: parseFloat(consensusIncEthForDate.toFixed(6)),
                executionIncomeEth: parseFloat(execIncEthForDate.toFixed(6)),
                price: price,
                consensusIncomeCurr: parseFloat((consensusIncEthForDate * price).toFixed(3)),
                executionIncomeCurr: parseFloat((execIncEthForDate * price).toFixed(3)),
                withdrawalsEth: parseFloat((withdrawalsForDate).toFixed(6)),
            })

            prevBalance = endOfDayBalance.balance;
        })
    }

    // Group by date
    if (groupByDate) {
        let groupedDataColumnValues: CsvDataColumnValue[] = [];
        let grouped = _.groupBy(dataColumnValues, (el) => el.date);

        for (const date in grouped) {
            let allRewardsForDate: CsvDataColumnValue[] = grouped[date];
            const price = parseFloat(AGGREGATE_REWARDS_DATA.eth_prices[date].toFixed(3));

            // Consensus income
            let consensusIncomeEth = 0;
            let consensusIncomeCurr = 0;
            let executionIncomeEth = 0;
            let executionIncomeCurr = 0;
            let withdrawalsEth = 0;
            let endOfDayBalance = 0;
            allRewardsForDate.forEach((reward) => {
                consensusIncomeEth += reward.consensusIncomeEth;
                executionIncomeEth += reward.executionIncomeEth;
                consensusIncomeCurr += reward.consensusIncomeCurr;
                executionIncomeCurr += reward.executionIncomeCurr;
                withdrawalsEth += reward.withdrawalsEth;
                endOfDayBalance += reward.endOfDayBalance;
            })

            groupedDataColumnValues.push({
                date: date,
                endOfDayBalance: parseFloat(endOfDayBalance.toFixed(6)),
                consensusIncomeEth: parseFloat(consensusIncomeEth.toFixed(6)),
                executionIncomeEth: parseFloat(executionIncomeEth.toFixed(6)),
                price: price,
                consensusIncomeCurr: parseFloat(consensusIncomeCurr.toFixed(3)),
                executionIncomeCurr: parseFloat(executionIncomeCurr.toFixed(3)),
                withdrawalsEth: parseFloat(withdrawalsEth.toFixed(6)),
            })
        }
        // Overwrite existing data with grouped data
        dataColumnValues = groupedDataColumnValues;
    }

    for (const dcv of dataColumnValues.sort(
        (a, b) => a.date.localeCompare(b.date))
        ) {
        csvRows.push(Object.values(dcv).join(separator));
    }
    const csv_string = csvRows.join('\n');

    // Download it as a file
    let filename = "combinedRewards.csv";
    if (validatorIndex != null) {
        filename = "rewards_" + validatorIndex + ".csv";
    }

    const link = document.createElement('a');
    link.style.display = 'none';
    link.setAttribute('target', '_blank');
    link.setAttribute('download', filename);

    if (window.Blob && window.URL) {
        // HTML5 Blob
        const blob = new Blob([csv_string], {
            type: 'text/csv;charset=utf-8'
        });
        const csvUrl = URL.createObjectURL(blob);
        link.setAttribute('href', csvUrl);
    } else {
        // Create the data URI manually
        link.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv_string));
    }

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

window.addEventListener("load", () => {
    const validatorChoiceTab = document.getElementById("validatorChoiceTab");
    // Validator choice form inputs - make them required if tab is active
    validatorChoiceTab.addEventListener("show.bs.tab", (event) => {
        const inputs = document.querySelector((event.target as HTMLElement).getAttribute("data-bs-target")).querySelectorAll("input");
        for (const input of inputs) {
            input.disabled = false;
        }
    });
    validatorChoiceTab.addEventListener("hide.bs.tab", (event) => {
        const inputs = document.querySelector((event.target as HTMLElement).getAttribute("data-bs-target")).querySelectorAll("input");
        for (let input of inputs) {
            input.disabled = true;
        }
    });
})

window.addEventListener("load", () => {
    document.getElementById("inputForm").addEventListener("submit", getRewards);

    // Scrolls validator-specific rewards table into view after clicking on the
    // "Show validator-specific details" button
    const rewardsTablesCollapse = document.getElementById('rewardsTablesCollapse');
    rewardsTablesCollapse.addEventListener('shown.bs.collapse', event => {
        (event.target as HTMLElement).scrollIntoView();
    })
})

window.addEventListener("load", () => {
    const addInputElements = document.getElementsByClassName("add-input-button");
    for (let i = 0; i < addInputElements.length; i++) {
        addInputElements[i].addEventListener("click", addInputElement);
    }
})
