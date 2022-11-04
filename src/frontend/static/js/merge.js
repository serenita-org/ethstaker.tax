const RECENT_EPOCH_COUNT = 15;
const NON_RECENT_EPOCH_IGNORE = 2;
const TTD = 58750000000000000000000;
const GWEI_MULTIPLIER = 1E9;
const HISTORICAL_DATA_EVERY = 25;

let TOTAL_ACTIVE_VALIDATORS = 460000; // Just a starting number, will be automatically adjusted
const EPOCH_BELLATRIX = 144896;
const EPOCH_MERGE = 146875;

const CHART_COLOR_RED = '#DB504A';
const CHART_COLOR_GREEN = '#308863';
const CHART_COLOR_ATT_SOURCE = '#308863';
const CHART_COLOR_ATT_TARGET = '#4ABF8E';
const CHART_COLOR_ATT_HEAD = '#A4DFC7';

let labels = [];
let indexesMissingDataSeries = [];
let indexesTimelySourceDataSeries = [];
let indexesTimelyTargetDataSeries = [];
let indexesTimelyHeadDataSeries = [];

let prevTotalDifficulty = 0;
// let totalDifficulty = 0;
let totalDifficulty = 58750003716598352816469;
// let currentBlockDifficulty = 11650000000000000;
let currentBlockDifficulty = 0;

let currentBlockNumber = "N/A";

let validatorInclusionData = {}

let attDataNonMissingRecentChart = null;
let attDataNonMissingChart = null;
let attDataMissingRecentChart = null;
let attDataMissingChart = null;
let totalDifficultyChart = null;
let validatorInclusionChart = null;

function initCharts() {
    const sharedChartOptions = {
        scales: {
            x: {
                ticks: {
                    precision: 0,
                },
                title: {
                    display: true,
                    text: "Epoch",
                },
                type: "linear",
            },
            y: {
                beginAtZero: true,
            },
        },
    }

    const historicalChartOptions = {
        plugins: {
            annotation: {
                annotations: {
                    bellatrix: {
                        type: 'line',
                        xMin: EPOCH_BELLATRIX,
                        xMax: EPOCH_BELLATRIX,
                        label: {
                            display: true,
                            content: "Bellatrix",
                            rotation: "auto",
                        }
                    },
                    merge: {
                        type: 'line',
                        xMin: EPOCH_MERGE,
                        xMax: EPOCH_MERGE,
                        label: {
                            display: true,
                            content: "The Merge",
                            rotation: "auto",
                        }
                    }
                }
            },
            zoom: {
                zoom: {
                    drag: {
                        enabled: true
                    },
                    mode: "x",
                }
            }
        }
    }

    attDataNonMissingRecentChart = new Chart(document.getElementById('attDataNonMissingRecentChart').getContext('2d'), {
        type: 'bar',
        options: {
            ...sharedChartOptions,
            ...{
                plugins: {
                    annotation: {
                        annotations: {
                            totalActive: {
                                type: 'line',
                                yMin: TOTAL_ACTIVE_VALIDATORS,
                                yMax: TOTAL_ACTIVE_VALIDATORS,
                                borderColor: "rgba(0,0,0,0.5)",
                                label: {
                                    display: true,
                                    content: "Active validators",
                                    backgroundColor: "rgba(0,0,0,0.5)"
                                }
                            },
                            superMajority: {
                                type: 'line',
                                yMin: 283333,
                                yMax: 283333,
                                borderColor: CHART_COLOR_ATT_SOURCE,
                                borderDash: [5],
                                label: {
                                    display: true,
                                    content: "Supermajority",
                                    backgroundColor: CHART_COLOR_ATT_SOURCE,
                                }
                            }
                        }
                    }
                }
            }
        }
    });

    attDataNonMissingChart = new Chart(document.getElementById('attDataNonMissingChart').getContext('2d'), {
        type: 'scatter',
        options: {
            ...sharedChartOptions,
            ...historicalChartOptions,
        }
    });
    attDataMissingRecentChart = new Chart(document.getElementById('attDataMissingRecentChart').getContext('2d'), {
        type: 'bar',
        options: {
            ...sharedChartOptions,
            ...{
                plugins: {
                    annotation: {
                        annotations: {
                            totalActive: {
                                type: 'line',
                                yMin: TOTAL_ACTIVE_VALIDATORS,
                                yMax: TOTAL_ACTIVE_VALIDATORS,
                                borderColor: "rgba(0,0,0,0.5)",
                                label: {
                                    display: true,
                                    content: "Active validators",
                                    backgroundColor: "rgba(0,0,0,0.5)"
                                }
                            },
                        }
                    }
                }
            }
        }
    });

    attDataMissingChart = new Chart(document.getElementById('attDataMissingChart').getContext('2d'), {
        type: 'scatter',
        options: {
            ...sharedChartOptions,
            ...historicalChartOptions,
        }
    });

    totalDifficultyChart = new Chart(document.getElementById('totalDifficultyChart').getContext('2d'), {
        type: 'bar',
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: false,
                    grace: "10%",
                    ticks: {
                        format: {
                            minimumSignificantDigits: 10,
                            maximumSignificantDigits: 10,
                        },
                    },
                    // 1.2E18 = about 100 blocks worth of difficulty, aka ~20min
                    suggestedMin: TTD - 1.2E18,
                    suggestedMax: TTD + 1.2E17,
                },
            },
            plugins: {
                title: {
                    display: true,
                    text: "Estimated time to reach TTD: loading..."
                },
                legend: {
                    display: false,
                }
            }
        }
    });

    validatorInclusionChart = new Chart(document.getElementById('validatorInclusionChart').getContext('2d'), {
        type: 'bar',
        options: {
            indexAxis: 'x',
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: 15000000,
                    title: {
                        display: true,
                        text: "Ether",
                    }
                },
            },
            plugins: {
                title: {
                    display: true,
                },
                legend: {
                    display: false,
                }
            }
        }
    });
}

function rateLimited() {
    console.error("You have been rate limited. Please make sure you only have this site open once. The data on this site will update automatically.");
    new bootstrap.Toast(document.getElementById("rateLimitedToast")).show();
}

async function getAttestationData() {
    labels = [];
    indexesMissingDataSeries = [];
    indexesTimelySourceDataSeries = [];
    indexesTimelyTargetDataSeries = [];
    indexesTimelyHeadDataSeries = [];

    const url = new URL("/api/v1/merge/attestation_data", window.location.href).href;
    await fetch(url)
        .then(function (response) {
            if (response.status === 429) {
                rateLimited();
            } else if (!response.ok) {
                throw new Error("Unexpected status code " + response.status + " received");
            }
            return response.json();
        })
        .then(data => {
                for (const epoch in data) {
                    labels.push(epoch);
                    indexesMissingDataSeries.push(data[epoch].indexes_missing);
                    indexesTimelySourceDataSeries.push(data[epoch].indexes_timely_source);
                    indexesTimelyTargetDataSeries.push(data[epoch].indexes_timely_target);
                    indexesTimelyHeadDataSeries.push(data[epoch].indexes_timely_head);
                }
            }
        )
}

async function getValidatorInclusionData() {
    validatorInclusionData = {};

    const url = new URL("/api/v1/merge/validator_inclusion", window.location.href).href;
    await fetch(url)
        .then(function (response) {
            if (response.status === 429) {
                rateLimited();
            } else if (!response.ok) {
                throw new Error("Unexpected status code " + response.status + " received");
            }
            return response.json();
        })
        .then(data => {
                validatorInclusionData = data;
            }
        )
}

async function getBlockNumber() {
    const url = new URL("/api/v1/merge/block_number", window.location.href).href;
    await fetch(url)
        .then(function (response) {
            if (response.status === 429) {
                rateLimited();
            } else if (!response.ok) {
                throw new Error("Unexpected status code " + response.status + " received");
            }
            return response.text();
        })
        .then(text => {
                currentBlockNumber = parseInt(text);
            }
        )
}

async function getTotalDifficulty() {
    const url = new URL("/api/v1/merge/total_difficulty", window.location.href).href;
    await fetch(url)
        .then(function (response) {
            if (response.status === 429) {
                rateLimited();
            } else if (!response.ok) {
                throw new Error("Unexpected status code " + response.status + " received");
            }
            return response.text();
        })
        .then(text => {
                totalDifficulty = parseInt(text);
            }
        )
}

function toggleDifficultyChartZero() {
    totalDifficultyChart.options.scales.x.beginAtZero = !totalDifficultyChart.options.scales.x.beginAtZero;
    totalDifficultyChart.update();
}

function updateProgress(progress) {
    let progressBar = document.querySelector("#progressBarUpdatingData");
    progressBar.style.width = `${progress}%`;
}

function updateAttestationDataCharts() {
    let historicalDataIndexes = labels.slice(0, -NON_RECENT_EPOCH_IGNORE).reduce(
        (res, epochNumber, currentIndex) => {
            if (epochNumber % HISTORICAL_DATA_EVERY === 0) res.push(currentIndex);
            return res
        }, []
    );

    attDataNonMissingChart.data.labels = [...labels.slice(0, -NON_RECENT_EPOCH_IGNORE)].filter((_, idx) => historicalDataIndexes.indexOf(idx) !== -1);
    attDataNonMissingChart.data.datasets = [{
        label: 'Timely source attestations',
        data: [...indexesTimelySourceDataSeries.slice(0, -NON_RECENT_EPOCH_IGNORE)].filter((_, idx) => historicalDataIndexes.indexOf(idx) !== -1),
        backgroundColor: [CHART_COLOR_ATT_SOURCE,],
        borderColor: [CHART_COLOR_ATT_SOURCE,],
    }, {
        label: 'Timely target attestations',
        data: [...indexesTimelyTargetDataSeries.slice(0, -NON_RECENT_EPOCH_IGNORE)].filter((_, idx) => historicalDataIndexes.indexOf(idx) !== -1),
        backgroundColor: [CHART_COLOR_ATT_TARGET,],
        borderColor: [CHART_COLOR_ATT_TARGET,],
    }, {
        label: 'Timely head attestations',
        data: [...indexesTimelyHeadDataSeries.slice(0, -NON_RECENT_EPOCH_IGNORE)].filter((_, idx) => historicalDataIndexes.indexOf(idx) !== -1),
        backgroundColor: [CHART_COLOR_ATT_HEAD,],
        borderColor: [CHART_COLOR_ATT_HEAD,],
    },]
    attDataNonMissingChart.update("none");

    attDataNonMissingRecentChart.data.labels = labels.slice(-RECENT_EPOCH_COUNT);
    attDataNonMissingRecentChart.data.datasets = [{
        label: 'Timely source attestations',
        data: indexesTimelySourceDataSeries.slice(-RECENT_EPOCH_COUNT),
        backgroundColor: [CHART_COLOR_ATT_SOURCE,],
        borderColor: [CHART_COLOR_ATT_SOURCE,],
    }, {
        label: 'Timely target attestations',
        data: indexesTimelyTargetDataSeries.slice(-RECENT_EPOCH_COUNT),
        backgroundColor: [CHART_COLOR_ATT_TARGET,],
        borderColor: [CHART_COLOR_ATT_TARGET,],
    }, {
        label: 'Timely head attestations',
        data: indexesTimelyHeadDataSeries.slice(-RECENT_EPOCH_COUNT),
        backgroundColor: [CHART_COLOR_ATT_HEAD,],
        borderColor: [CHART_COLOR_ATT_HEAD,],
    },]
    attDataNonMissingRecentChart.options.plugins.annotation.annotations.totalActive.yMin = TOTAL_ACTIVE_VALIDATORS;
    attDataNonMissingRecentChart.options.plugins.annotation.annotations.totalActive.yMax = TOTAL_ACTIVE_VALIDATORS;
    attDataNonMissingRecentChart.update("none");

    attDataMissingChart.data.labels = [...labels.slice(0, -NON_RECENT_EPOCH_IGNORE)].filter((_, idx) => historicalDataIndexes.indexOf(idx) !== -1);
    attDataMissingChart.data.datasets = [{
        label: 'Missing attestations',
        data: [...indexesMissingDataSeries.slice(0, -NON_RECENT_EPOCH_IGNORE)].filter((_, idx) => historicalDataIndexes.indexOf(idx) !== -1),
        backgroundColor: [CHART_COLOR_RED,],
        borderColor: [CHART_COLOR_RED,],
    },]
    attDataMissingChart.update("none");

    attDataMissingRecentChart.data.labels = labels.slice(-RECENT_EPOCH_COUNT);
    attDataMissingRecentChart.data.datasets = [{
        label: 'Missing attestations',
        data: indexesMissingDataSeries.slice(-RECENT_EPOCH_COUNT),
        backgroundColor: [CHART_COLOR_RED,],
        borderColor: [CHART_COLOR_RED,],
    },]
    attDataMissingRecentChart.options.plugins.annotation.annotations.totalActive.yMin = TOTAL_ACTIVE_VALIDATORS;
    attDataMissingRecentChart.options.plugins.annotation.annotations.totalActive.yMax = TOTAL_ACTIVE_VALIDATORS;
    attDataMissingRecentChart.update("none");
}

async function updateTotalDifficultyData() {
    prevTotalDifficulty = totalDifficulty;

    // No need to call this API anymore
    // await getTotalDifficulty();

    if (totalDifficulty > TTD) {
        totalDifficultyChart.options.plugins.title.text=`Terminal Total Difficulty reached!`;
    } else if (prevTotalDifficulty > 0) {
        let difficultyDiff = totalDifficulty - prevTotalDifficulty;
        if (difficultyDiff !== 0) {
            let blockDifference = Math.round(difficultyDiff / currentBlockDifficulty);
            currentBlockDifficulty = Math.round(difficultyDiff / blockDifference);
            let estBlocksRemaining = (TTD - totalDifficulty) / (difficultyDiff/blockDifference);
            let estTimeRemainingSeconds = estBlocksRemaining * 14;
            let estMergeDate = new Date(new Date().getTime() + 1000 * estTimeRemainingSeconds);
            totalDifficultyChart.options.plugins.title.text=`Estimated time to reach TTD: ${estMergeDate.toLocaleString()} (~ ${Math.floor(estBlocksRemaining)} blocks)`;
        }
    }

    // Update chart
    totalDifficultyChart.data.labels = ["Total Difficulty", "TTD"]
    totalDifficultyChart.data.datasets = [{
        data: [totalDifficulty, TTD],
        backgroundColor: [CHART_COLOR_GREEN, CHART_COLOR_RED,],
    }]
    totalDifficultyChart.update("none");
}

async function updateValidatorInclusionData() {
    await getValidatorInclusionData();

    let maxEpochNumber = Math.max(...Object.keys(validatorInclusionData));

    // Update active validator count
    TOTAL_ACTIVE_VALIDATORS = validatorInclusionData[maxEpochNumber]["current_epoch_active_gwei"] / (31.5 * GWEI_MULTIPLIER)

    // Update charts
    if (validatorInclusionData[maxEpochNumber] !== undefined) {
        validatorInclusionChart.options.plugins.annotation = {
            annotations: {
                totalActive: {
                    type: 'line',
                    yMin: validatorInclusionData[maxEpochNumber]["current_epoch_active_gwei"] / GWEI_MULTIPLIER,
                    yMax: validatorInclusionData[maxEpochNumber]["current_epoch_active_gwei"] / GWEI_MULTIPLIER,
                    borderColor: "rgba(0,0,0,0.3)",
                    label: {
                        display: true,
                        content: "Total active stake",
                        backgroundColor: "rgba(0,0,0,0.3)"
                    }
                },
                superMajority: {
                    type: 'line',
                    yMin: (validatorInclusionData[maxEpochNumber]["current_epoch_active_gwei"] / GWEI_MULTIPLIER) * 2/3,
                    yMax: (validatorInclusionData[maxEpochNumber]["current_epoch_active_gwei"] / GWEI_MULTIPLIER) * 2/3,
                    borderColor: CHART_COLOR_ATT_TARGET,
                    borderDash: [5],
                    label: {
                        display: true,
                        content: "Supermajority",
                        backgroundColor: CHART_COLOR_ATT_TARGET,
                    }
                }
            }
        }

        validatorInclusionChart.data.labels = [`Epoch ${maxEpochNumber - 1} target attesting`, `Epoch ${maxEpochNumber - 1} head attesting`, `Epoch ${maxEpochNumber} target attesting`]
        validatorInclusionChart.data.datasets = [{
            data: [validatorInclusionData[maxEpochNumber]["previous_epoch_target_attesting_gwei"] / GWEI_MULTIPLIER, validatorInclusionData[maxEpochNumber]["previous_epoch_head_attesting_gwei"] / GWEI_MULTIPLIER, validatorInclusionData[maxEpochNumber]["current_epoch_target_attesting_gwei"] / GWEI_MULTIPLIER],
            backgroundColor: [CHART_COLOR_ATT_TARGET, CHART_COLOR_ATT_HEAD, CHART_COLOR_ATT_TARGET],
        }]
        validatorInclusionChart.update("none");
    }
}

async function updateAttestationData() {
    // Indicate that we're updating
    updateProgress(100);
    await new Promise(r => setTimeout(r, 1000));

    await getAttestationData();
    updateAttestationDataCharts();

    updateProgress(0);
}

function getCurrentSlotNumber() {
    return Math.floor((new Date().getTime() - new Date(1606824023 * 1000).getTime()) / 12000);
}

function updateCurrentEpochProgress() {
    let progressBar = document.querySelector("#progressBarEpochProgress");
    let progress = Math.floor(100 * (getCurrentSlotNumber() % 32 / 32));
    progressBar.style.width = `${progress}%`;
    let progressTextElement = document.querySelector("#epochProgressText");
    progressTextElement.innerText = `Epoch ${Math.floor(getCurrentSlotNumber() / 32)} slot ${getCurrentSlotNumber() % 32}/32`;
}

function updateImage() {
    const pandaImages = document.getElementsByClassName("pandaImage");
    for (const i of pandaImages) {
        i.style.display = 'none';
    }

    // Update panda image in header
    let activeImage;
    if (totalDifficulty >= TTD) {
        // Panda 3
        activeImage = document.getElementById("pandaImage3");
    } else if (totalDifficulty > TTD - 1.2E18) {
        // Panda 2 - we're close
        activeImage = document.getElementById("pandaImage2");
    } else {
        // Panda 1
        activeImage = document.getElementById("pandaImage1");
    }
    activeImage.style.display = "flex";
}

async function updateBlockNumber() {
    await getBlockNumber();
    document.getElementById("currentBlockNumber").innerHTML = `<b><a href="https://etherscan.io/block/${currentBlockNumber}" target=_blank">${currentBlockNumber.toLocaleString()}</a></b>`;
}

document.addEventListener("DOMContentLoaded", function () {
    initCharts();

    updateAttestationData();
    setInterval(updateAttestationData, 30000);

    // Run it once to show the chart
    updateTotalDifficultyData();
    // setInterval(updateTotalDifficultyData, 15000);

    // updateBlockNumber();
    // setInterval(updateBlockNumber, 15000);

    updateValidatorInclusionData();
    setInterval(updateValidatorInclusionData, 30000);

    updateCurrentEpochProgress();
    setInterval(updateCurrentEpochProgress, 500);

    updateImage();
    setInterval(updateImage, 1000);
});
