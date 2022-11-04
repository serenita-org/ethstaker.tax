function addInputElement(e) {
    inputGroup = e.parentElement;
    inputGroupContainer = inputGroup.parentElement;
    newInputGroup = inputGroup.cloneNode(deep=true);
    newInputGroup.classList.add("input-element-to-remove");

    // Set value to empty for cloned input element
    newInputGroup.children[0].value = "";

    // Add a remove button to the new input group if there is no remove button present
    if (newInputGroup.children.length == 2) {
        removeButton = document.createElement("button");
        removeButton.className = "btn btn-outline-secondary input-element-remove";
        removeButton.setAttribute("type", "button");
        removeButton.innerHTML = "<i class='bi-dash-circle'></i> Remove";
        newInputGroup.appendChild(removeButton);
    }

    // Add the new input group to the parent input group container
    inputGroupContainer.appendChild(newInputGroup);

    // Focus on the new input element - so the user doesn't have to
    // select it to continue typing
    newInputGroup.children[0].focus()
}

function initDatePickers() {

}

function showCustomDateRangeInput(show) {
    element = document.getElementById("customDateRangeInput");
    if (show) {
        element.classList.remove("d-none");
    } else {
        element.classList.add("d-none");
    }
}

function selectDateRangeByYear() {
    selectDateRangeElement = document.getElementById("selectDateRange");

    // Toggle datepicker visibility depending on selected date range
    if (selectDateRangeElement.value == "custom") {
        // Selected custom date, show datepickers
        showCustomDateRangeInput(true);

        // Init Pikaday date pickers
        datePickerIds = ["datePickerStart", "datePickerEnd"];
        datePickerIds.forEach((elementId) => {
            var picker = new Pikaday({
                field: document.getElementById(elementId),
                format: "YYYY-MM-DD"
            });
        });
    } else if (selectDateRangeElement.value == "since_genesis") {
        // Selected since genesis as the date, hide datepickers
        showCustomDateRangeInput(false);

        startDatePicker = document.getElementById("datePickerStart");
        // Genesis was Dec 12th 12PM UTC, which may have still been November 30th in some timezones
        startDatePicker.value = "2020-11-30";

        endDatePicker = document.getElementById("datePickerEnd");
        // toISOString first converts to UTC - handle that by adding the timezone offset
        var endDate = new Date();
        const offset = endDate.getTimezoneOffset();
        endDate = new Date(endDate.getTime() - (offset*60*1000));
        endDatePicker.value = endDate.toISOString().split('T')[0];
    } else {
        // Selected a year as a date, hide datepickers
        showCustomDateRangeInput(false);

        startDatePicker = document.getElementById("datePickerStart");
        startDatePicker.value = selectDateRangeElement.value  + "-01-01";

        endDatePicker = document.getElementById("datePickerEnd");
        endDatePicker.value = selectDateRangeElement.value  + "-12-31";
    }
}

window.addEventListener("load", initDatePickers);

window.addEventListener("load", () => {
    selectDateRangeElement = document.getElementById("selectDateRange");
    selectDateRangeElement.addEventListener("change", selectDateRangeByYear);
    showCustomDateRangeInput(false);
    selectDateRangeByYear();
})

async function handleErrorMessage(response) {
    const {status} = response;

    const text = await response.text();
    try {
        const parsed = JSON.parse(text);
        if (status == 200) {
            return parsed;
        } else {
            return Promise.reject(new Error(JSON.stringify(parsed)));
        }
    } catch(err) {
        throw new Error(text)
    }
}

function cleanupFromPreviousRequest() {
    rewardsTablesContainer = document.getElementById("rewardsTablesContainer");
    // Remove children elements
    while (rewardsTablesContainer.firstChild) {
        rewardsTablesContainer.firstChild.remove()
    }

    combinedRewardsTable = document.getElementById("combinedRewardsTable");
    // Remove children elements
    while (combinedRewardsTable.firstChild) {
        combinedRewardsTable.firstChild.remove()
    }

    sumRewardsTablesContainer = document.getElementById("sumRewardsTablesContainer");
    // Remove children tables
    while (sumRewardsTablesContainer.firstChild) {
        sumRewardsTablesContainer.firstChild.remove()
    }

    // Collapse
    rewardsTablesCollapse = document.getElementById("rewardsTablesCollapse");
    rewardsTablesCollapse.classList.remove("show");

    // Hide error message
    document.getElementById("calculateErrorMessage").classList.add("d-none");
}

function enableCalculateButton(enabled) {
    document.getElementById("calculateButton").disabled = !enabled;

    document.getElementById("calculateButton").disabled = !enabled;
}

function showCalculateMessage(show) {
    if (show) {
        document.getElementById("calculateInfoMessage").classList.remove("d-none");
    }
    else {
        document.getElementById("calculateInfoMessage").classList.add("d-none");
    }
}

function showErrorMessage(message) {
    document.getElementById("calculateErrorMessage").classList.remove("d-none");
    document.getElementById("calculateErrorMessage").innerText = message;
    enableCalculateButton(true);
    showCalculateMessage(false);
}

function compareValues(a, b) {
    // return -1/0/1 based on what you "know" a and b
    // are here. Numbers, text, some custom case-insensitive
    // and natural number ordering, etc. That's up to you.
    // A typical "do whatever JS would do" is:
    return (a<b) ? -1 : (a>b) ? 1 : 0;
}

function sortTable(table, colnum) {
    // get all the rows in this table:
    let rows = Array.from(table.querySelectorAll(`tr`));

    // but ignore the heading row:
    rows = rows.slice(1);

    // set up the queryselector for getting the indicated
    // column from a row, so we can compare using its value:
    let qs = `th:nth-child(${colnum})`;

    // and then just... sort the rows:
    rows.sort( (r1,r2) => {
        // get each row's relevant column
        let t1 = r1.querySelector(qs);
        let t2 = r2.querySelector(qs);

        // and then effect sorting by comparing their content:
        return compareValues(t1.textContent, t2.textContent);
    });

    // and then the magic part that makes the sorting appear on-page:
    rows.forEach(row => table.appendChild(row));
}

function getRewardsForValidatorIndexes(validatorIndexes) {
    var params = new URLSearchParams();

    validatorIndexes.forEach((validatorIndex) => {
        params.append("validator_indexes", validatorIndex);
    })

    params.append("start_date", document.getElementById("datePickerStart").value)
    params.append("end_date", document.getElementById("datePickerEnd").value)

    params.append("timezone", "UTC")

    params.append("currency", document.getElementById("selectCurrency").value)

    var url = new URL("/api/v1/rewards", window.location.href)
    url.search = params.toString();

    fetch(url)
        .then(handleErrorMessage)
        .then(data => {
            // Sum total rewards over all validators
            sumTotalIncomeEth = 0;
            sumTotalIncomeCurr = 0;
            currency = null;

            // Add a summary table for the total income over all validators
            sumTotalDescriptionP = document.createElement("p");
            sumTotalDescriptionP.innerText = "The following table shows the total rewards of all of your validators for the selected date range.";
            sumRewardsTablesContainer.appendChild(sumTotalDescriptionP);
            sumTotalTable = document.createElement("table");
            sumTotalTable.classList.add("table");
            sumRewardsTablesContainer = document.getElementById("sumRewardsTablesContainer");
            sumRewardsTablesContainer.appendChild(sumTotalTable);

            // Add a button to download a combined CSV export of the rewards
            btn = document.createElement("a");
            btn.classList.add("btn");
            btn.classList.add("btn-primary");
            btn.classList.add("m-3");
            btn.id = "combinedCsvExport";
            btn.innerText = "Download CSV of daily rewards for all validators";
            btn.role = "button";
            sumRewardsTablesContainer.appendChild(btn);

            // Add a button to expand the collapsed details
            btn = document.createElement("a");
            btn.classList.add("btn");
            btn.classList.add("btn-secondary");
            btn.classList.add("m-3");
            btn.href = "#rewardsTablesCollapse";
            btn.innerText = "Show validator-specific details";
            btn.role = "button";
            btn.setAttribute("data-bs-toggle", "collapse");
            btn.setAttribute("data-bs-target", "#rewardsTablesCollapse");
            sumRewardsTablesContainer.appendChild(btn);

            // Populate an invisible table containing the combined
            // rewards for all validators to enable the combined CSV export
            currency = data.currency;
            let rewardTableColumnNames = [
                "Date",
                "Validator Index",
                "End-of-day validator balance [ETH]",
                "Consensus layer income [ETH]",
                "Execution layer income [ETH]",
                "Price [ETH/" + currency + "]",
                "Consensus layer income [" + currency + "]",
                "Execution layer income [" + currency + "]"
            ];
            combinedRewardsTable = document.getElementById("combinedRewardsTable")

            // Table head & body
            combinedRewardsTableHead = document.createElement("thead");
            combinedRewardsTableHeaderRow = document.createElement("tr");
            combinedRewardsTableBody = document.createElement("tbody");

            rewardTableColumnNames.forEach((columnName) => {
                headerColumn = document.createElement("th");
                headerColumn.innerText=columnName;
                combinedRewardsTableHeaderRow.appendChild(headerColumn);
            });

            combinedRewardsTableHead.appendChild(combinedRewardsTableHeaderRow);

            combinedRewardsTable.appendChild(combinedRewardsTableHead);
            combinedRewardsTable.appendChild(combinedRewardsTableBody);


            // Create a table for each validators' rewards
            rewardsTablesContainer = document.getElementById("rewardsTablesContainer");
            data.validator_rewards.forEach(
                ({
                     eod_balances, initial_balance, validator_index,
                     exec_layer_block_rewards,
                     total_consensus_layer_eth, total_consensus_layer_currency,
                     total_execution_layer_eth, total_execution_layer_currency
                }) => {
                // Wrapper div
                divElement = document.createElement("div");
                divElement.classList.add("m-3");

                // Table description
                descriptionDivElement = document.createElement("div");
                descriptionDivElement.classList.add("d-inline");
                paragraph = document.createElement("p");
                paragraph.classList.add("lead");
                paragraph.classList.add("d-inline");
                paragraph.innerText = "Rewards for validator index " + validator_index;
                descriptionDivElement.appendChild(paragraph);
                divElement.appendChild(descriptionDivElement);

                // CSV download button
                link = document.createElement("a");
                link.href = "#";
                link.classList.add("btn");
                link.classList.add("btn-primary");
                link.classList.add("csv-export");
                link.classList.add("m-3");
                link.role = "button";
                link.innerText = "CSV";
                divElement.appendChild(link);

                tableElement = document.createElement("table");
                tableElement.id = "rewards_table_" + validator_index;
                tableElement.classList.add("table");

                // Table head
                tableHead = document.createElement("thead");
                headerRow = document.createElement("tr");

                rewardTableColumnNames.forEach((columnName) => {
                    if (columnName !== "Validator Index") {
                        headerColumn = document.createElement("th");
                        headerColumn.innerText=columnName;
                        headerRow.appendChild(headerColumn);
                    }
                });

                tableHead.appendChild(headerRow);

                // Table body
                tableBody = document.createElement("tbody");

                if (initial_balance !== null) {
                    var prevBalance = initial_balance.balance;
                } else {
                    var prevBalance = 0;
                }
                eod_balances.forEach((balance) => {
                    bodyRow = document.createElement("tr");
                    combinedRewardsTableBodyRow = document.createElement("tr");

                    // Date
                    dateColumn = document.createElement("th");
                    dateColumn.innerText = balance.date;
                    bodyRow.appendChild(dateColumn);
                    combinedRewardsTableBodyRow.appendChild(dateColumn.cloneNode(true));

                    // Validator index (only) for the combined table
                    valIndexColumnValue = document.createElement("th");
                    valIndexColumnValue.innerText = validator_index;
                    combinedRewardsTableBodyRow.appendChild(valIndexColumnValue);

                    // End-of-day validator balance [ETH]
                    eodValidatorBalanceColumn = document.createElement("th");
                    eodValidatorBalanceColumn.innerText = balance.balance;
                    bodyRow.appendChild(eodValidatorBalanceColumn);
                    combinedRewardsTableBodyRow.appendChild(eodValidatorBalanceColumn.cloneNode(true));

                    // Consensus layer income [ETH]
                    consensusIncEthForDate = balance.balance - prevBalance;
                    consensusIncEthColumn = document.createElement("th");
                    consensusIncEthColumn.innerText = consensusIncEthForDate;
                    bodyRow.appendChild(consensusIncEthColumn);
                    combinedRewardsTableBodyRow.appendChild(consensusIncEthColumn.cloneNode(true));

                    // Execution layer income [ETH]
                    execIncEthForDate = 0;
                    exec_layer_block_rewards.filter(br => br.date === balance.date).forEach((br) => {
                        execIncEthForDate += br.reward;
                    })
                    execIncEthColumn = document.createElement("th");
                    execIncEthColumn.innerText = execIncEthForDate;
                    bodyRow.appendChild(execIncEthColumn);
                    combinedRewardsTableBodyRow.appendChild(execIncEthColumn.cloneNode(true));

                    // Price [ETH/currency]
                    priceForDate = data.eth_prices[balance.date];
                    priceEthColumn = document.createElement("th");
                    priceEthColumn.innerText = priceForDate
                    bodyRow.appendChild(priceEthColumn);
                    combinedRewardsTableBodyRow.appendChild(priceEthColumn.cloneNode(true));

                    // Consensus layer income [currency]
                    consensusIncCurrForDate = priceForDate * consensusIncEthForDate;
                    consensusIncCurrColumn = document.createElement("th");
                    consensusIncCurrColumn.innerText = consensusIncCurrForDate;
                    bodyRow.appendChild(consensusIncCurrColumn);
                    combinedRewardsTableBodyRow.appendChild(consensusIncCurrColumn.cloneNode(true));

                    // Execution layer income [currency]
                    executionIncCurrForDate = priceForDate * execIncEthForDate;
                    executionIncCurrColumn = document.createElement("th");
                    executionIncCurrColumn.innerText = executionIncCurrForDate;
                    bodyRow.appendChild(executionIncCurrColumn);
                    combinedRewardsTableBodyRow.appendChild(executionIncCurrColumn.cloneNode(true));

                    prevBalance = balance.balance;
                    tableBody.appendChild(bodyRow);
                    combinedRewardsTableBody.appendChild(combinedRewardsTableBodyRow.cloneNode(true));
                });
                tableElement.appendChild(tableBody);

                // Table foot
                tableFoot = document.createElement("tfoot");

                footRow = document.createElement("tr");

                // Under Date column
                footColumn = document.createElement("td");
                footColumn.innerText="Total:";
                footRow.appendChild(footColumn);

                // Under End-of-day balance column
                footColumn = document.createElement("td");
                footRow.appendChild(footColumn);

                // Under consensus layer income [ETH] column
                footColumn = document.createElement("td");
                footColumn.innerText=total_consensus_layer_eth;
                footRow.appendChild(footColumn);

                // Under exec layer income [ETH] column
                footColumn = document.createElement("td");
                footColumn.innerText=total_execution_layer_eth;
                footRow.appendChild(footColumn);

                // Under price column
                footColumn = document.createElement("td");
                footRow.appendChild(footColumn);

                // Under consensus layer income [currency] column
                footColumn = document.createElement("td");
                footColumn.innerText=total_consensus_layer_currency;
                footRow.appendChild(footColumn);

                // Under exec layer income [currency] column
                footColumn = document.createElement("td");
                footColumn.innerText=total_execution_layer_currency;
                footRow.appendChild(footColumn);

                tableFoot.appendChild(footRow);

                // Add all parts to the table
                tableElement.appendChild(tableHead);
                tableElement.appendChild(tableBody);
                tableElement.appendChild(tableFoot);

                divElement.appendChild(tableElement);

                rewardsTablesContainer.appendChild(divElement);

                sumTotalIncomeEth += total_consensus_layer_eth + total_execution_layer_eth;
                sumTotalIncomeCurr += total_consensus_layer_currency + total_execution_layer_currency;
            })

            // Sort combined rewards table by date (1st column)
            sortTable(combinedRewardsTable, 1);

            // Populate sum of total income table
            tableHead = document.createElement("thead");
            headerRow = document.createElement("tr");
            tableHead.appendChild(headerRow);

            let columnNames = [
                "Total income [ETH]",
                "Total income [" + currency + "]"
            ];
            columnNames.forEach((columnName) => {
                headerColumn = document.createElement("th");
                headerColumn.innerText = columnName;
                headerRow.appendChild(headerColumn);
            });
            sumTotalTable.appendChild(tableHead);

            tableBody = document.createElement("tbody");
            bodyRow = document.createElement("tr");
            tableBody.appendChild(bodyRow);

            let columnValues = [
                sumTotalIncomeEth,
                sumTotalIncomeCurr
            ];
            columnValues.forEach((columnValue) => {
                bodyColumn = document.createElement("td");
                bodyColumn.innerText = columnValue;
                bodyRow.appendChild(bodyColumn);
            })
            sumTotalTable.appendChild(tableBody);

            enableCalculateButton(true);
            showCalculateMessage(false);

            // Scroll to bottom to show resulting table
            window.scrollTo(0, document.body.scrollHeight);
        })
        .catch(error => {
            if (error.toString().indexOf("Too Many Requests") > -1) {
                errorMessage = "You have been rate limited, please try again later.";
            } else {
                errorMessage = "An error occurred, please try again. If the issue persists, check the browser console for more information.";
            }
            showErrorMessage(errorMessage);
            console.error('An error occurred while fetching rewards:', error);
        });
}

async function getRewards() {
    // Depending on the selected tab, it may be needed to fetch the
    // validator indexes first
    tabElements = document.getElementById("validatorChoiceTab").children;
    activeTab = null;
    for (var i = 0; i < tabElements.length; i++) {
        if (tabElements[i].children[0].className.includes("active")) {
            activeTab = tabElements[i].children[0];
        }
    }

    cleanupFromPreviousRequest();

    // Disable the calculate button to avoid users clicking it multiple times
    enableCalculateButton(false);

    // Show message that it may take a while
    showCalculateMessage(true);

    if (activeTab.textContent == "Validator Indexes") {
        var validatorIndexes = Array();

        indexInputGroups = document.getElementById("index").children;
        for (var i = 0; i < indexInputGroups.length; i++) {
            indexInput = indexInputGroups[i].children[0];

            indexInput.required = true;
            if (!indexInput.checkValidity()) {
                indexInput.required = false;
                showErrorMessage("Invalid validator index: " + indexInput.value);
                return false;
            }
            indexInput.required = false;

            validatorIndexes.push(indexInput.value);
        }
        getRewardsForValidatorIndexes(validatorIndexes);
    }
    else if (activeTab.textContent == "Validator public keys") {
        var pubKeyUrl = new URL("/api/v1/index_for_publickey", window.location.href)

        let pubKeyInputGroups = document.getElementById("pubkey").children;

        const request = async (url) => {
            const response = await fetch(url);
            try {
                data = await handleErrorMessage(response);
                return data;
            } catch(error) {
                showErrorMessage(error);
                return false;
            }
        }

        var indexRequests = Array();
        for (var i = 0; i < pubKeyInputGroups.length; i++) {
            pubKeyInput = pubKeyInputGroups[i].children[0];

            pubKeyInput.required = true;
            if (!pubKeyInput.checkValidity()) {
                pubKeyInput.required = false;
                showErrorMessage("Invalid public key: " + pubKeyInput.value);
                return false;
            }
            pubKeyInput.required = false;

            var pubKeyParams = new URLSearchParams();
            pubKeyParams.append("publickey", pubKeyInput.value);
            pubKeyUrl.search = pubKeyParams.toString();

            indexRequests.push(request(pubKeyUrl));
        }
        let validatorIndexes = await Promise.all(indexRequests)
        getRewardsForValidatorIndexes(validatorIndexes);
    }
    else if (activeTab.textContent == "ETH1 deposit addresses") {
        var depositAddrUrl = new URL("/api/v1/indexes_for_eth1_address", window.location.href)

        let depositAddrInputGroups = document.getElementById("eth1").children;

        const request = async (url) => {
            const response = await fetch(url);
            try {
                data = await handleErrorMessage(response);
                return data;
            } catch (error) {
                showErrorMessage(error);
                throw error
            }
        }

        var validatorIndexes = Array();
        for (var i = 0; i < depositAddrInputGroups.length; i++) {
            depositAddrInput = depositAddrInputGroups[i].children[0];

            depositAddrInput.required = true;
            if (!depositAddrInput.checkValidity()) {
                depositAddrInput.required = false;
                showErrorMessage("Invalid deposit address: " + depositAddrInput.value);
                return false;
            }
            depositAddrInput.required = false;

            var depositAddrParams = new URLSearchParams();
            depositAddrParams.append("eth1_address", depositAddrInput.value);
            depositAddrUrl.search = depositAddrParams.toString();

            const response = await fetch(depositAddrUrl);
            try {
                data = await handleErrorMessage(response);
                validatorIndexes = validatorIndexes.concat(data);
            } catch (error) {
                showErrorMessage(error);
                throw error
            }
        }
        getRewardsForValidatorIndexes(validatorIndexes);
    } else {
        showErrorMessage("Invalid tab selected");
    }
}

// Quick and simple export a HTML table into a csv
function downloadTableAsCsv(table, separator = ';') {
    // Select table rows
    var rows = table.getElementsByTagName("tr");
    // Construct csv
    var csv = [];
    for (var i = 0; i < rows.length; i++) {
        var row = [], cols = rows[i].querySelectorAll('td, th');
        for (var j = 0; j < cols.length; j++) {
            // Clean innerText to remove multiple spaces and jumpline (break csv)
            var data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ')
            // Escape double-quote with double-double-quote (see https://stackoverflow.com/questions/17808511/properly-escape-a-double-quote-in-csv)
            data = data.replace(/"/g, '""');
            // Push escaped string
            row.push('"' + data + '"');
        }
        csv.push(row.join(separator));
    }
    var csv_string = csv.join('\n');

    // Download it as a file
    var filename = table.id + '.csv';

    var link = document.createElement('a');
    link.style.display = 'none';
    link.setAttribute('target', '_blank');
    link.setAttribute('download', filename);

    if (window.Blob && window.URL) {
        // HTML5 Blob
        var blob = new Blob([csv_string], {
            type: 'text/csv;charset=utf-8'
        });
        var csvUrl = URL.createObjectURL(blob);
        link.setAttribute('href', csvUrl);
    } else {
        // Create the data URI manually
        link.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv_string));
    }

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

document.addEventListener('click', function (event) {
    // Remove input element buttons
    if (event.target.matches('.input-element-remove')) {
        inputGroupElement = event.target.parentElement;
        inputGroupElement.parentElement.removeChild(inputGroupElement);
    }

    // Combined CSV export
    if (event.target.matches("#combinedCsvExport")) {
        downloadTableAsCsv(document.getElementById("combinedRewardsTable"));
        event.preventDefault();
    }

    // Per-table CSV export
    if (event.target.matches('.csv-export')) {
        downloadTableAsCsv(event.target.parentElement.getElementsByTagName("table")[0]);
        event.preventDefault();
    }
}, false);

function getCookieValue(name) {
    return document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)')?.pop() || ''
}

function getSelectValues(selectElement)
{
    var values = Array();
    for (var option of selectElement.options) {
        values.push(option.value);
    }
    return values;
}

function populateInputsFromCookies() {
    const currencyInput = document.getElementById("selectCurrency");
    if (getSelectValues(currencyInput).indexOf(getCookieValue("currency")) !== -1) {
        currencyInput.value = getCookieValue("currency");
    }
}

window.addEventListener("load", function () {
    // populateInputsFromCookies();
})
