const API_BASE_URL =
  "http://127.0.0.1:8000";

const reportOutput =
  document.getElementById("reportOutput");

const dashboardOutput = document.getElementById("dashboardOutput");
const reportStatusBadge = document.getElementById("reportStatusBadge");
const dashboardWinner = document.getElementById("dashboardWinner");
const dashboardResultType = document.getElementById("dashboardResultType");
const dashboardConfidence = document.getElementById("dashboardConfidence");
const confidenceMeter = document.getElementById("confidenceMeter");
const dashboardRating = document.getElementById("dashboardRating");
const ratingMeter = document.getElementById("ratingMeter");
const dashboardMotm = document.getElementById("dashboardMotm");
const comparisonHomeTeam = document.getElementById("comparisonHomeTeam");
const comparisonAwayTeam = document.getElementById("comparisonAwayTeam");
const comparisonRows = document.getElementById("comparisonRows");
const dashboardSummary = document.getElementById("dashboardSummary");
const dashboardTactical = document.getElementById("dashboardTactical");
const dashboardKeyMoments = document.getElementById("dashboardKeyMoments");
const dashboardIndicators = document.getElementById("dashboardIndicators");
const dashboardVerdict = document.getElementById("dashboardVerdict");
const dashboardPlayerRatings = document.getElementById("dashboardPlayerRatings");
const playerCountBadge = document.getElementById("playerCountBadge");
const playerRatingsChartCanvas = document.getElementById("playerRatingsChart");
const chartFallback = document.getElementById("chartFallback");
const reportSection = document.getElementById("reportSection");
const loadingOverlay = document.getElementById("loadingOverlay");
const loadingMessage = document.getElementById("loadingMessage");
const loadingProgress = document.getElementById("loadingProgress");
const loadingStage = document.getElementById("loadingStage");
const loadingPercent = document.getElementById("loadingPercent");
const downloadPdfButton = document.getElementById("downloadPdfButton");

let playerRatingsChart = null;
let loadingTimers = [];
let loadingStartedAt = 0;

const historyOutput =
  document.getElementById("historyOutput");

const matchHeader =
  document.getElementById("matchHeader");

const generateButton =
  document.getElementById("generateButton");

const squadStatus =
  document.getElementById("squadStatus");

const squadSelectionSection =
  document.getElementById(
    "squadSelectionSection"
  );

const selectedPlayersSection =
  document.getElementById(
    "selectedPlayersSection"
  );

const homeSquadList =
  document.getElementById("homeSquadList");

const awaySquadList =
  document.getElementById("awaySquadList");

const homeSquadHeader =
  document.getElementById("homeSquadHeader");

const awaySquadHeader =
  document.getElementById("awaySquadHeader");

const selectedPlayersTable =
  document.getElementById(
    "selectedPlayersTable"
  );

const manOfTheMatchSelect =
  document.getElementById(
    "manOfTheMatch"
  );

const playerPerformancesInput =
  document.getElementById(
    "playerPerformances"
  );

const loadHomeSquadButton =
  document.getElementById(
    "loadHomeSquadButton"
  );

const loadAwaySquadButton =
  document.getElementById(
    "loadAwaySquadButton"
  );

const clearSelectedPlayersButton =
  document.getElementById(
    "clearSelectedPlayersButton"
  );


let homeSquad = [];
let awaySquad = [];
let selectedPlayers = [];


loadHomeSquadButton.addEventListener(
  "click",
  async function () {
    const teamName =
      document
        .getElementById("homeTeam")
        .value
        .trim();

    await loadSquad(
      teamName,
      "home"
    );
  }
);


loadAwaySquadButton.addEventListener(
  "click",
  async function () {
    const teamName =
      document
        .getElementById("awayTeam")
        .value
        .trim();

    await loadSquad(
      teamName,
      "away"
    );
  }
);


clearSelectedPlayersButton.addEventListener(
  "click",
  function () {
    selectedPlayers = [];

    document
      .querySelectorAll(
        ".player-checkbox"
      )
      .forEach(function (checkbox) {
        checkbox.checked = false;
      });

    renderSelectedPlayers();
  }
);


document
  .getElementById("matchForm")
  .addEventListener(
    "submit",
    async function (event) {
      event.preventDefault();

      updateHiddenPlayerPerformances();

      const matchData = {
        homeTeam:
          document
            .getElementById("homeTeam")
            .value
            .trim(),

        awayTeam:
          document
            .getElementById("awayTeam")
            .value
            .trim(),

        finalScore:
          document
            .getElementById("finalScore")
            .value
            .trim(),

        goalscorers:
          document
            .getElementById("goalscorers")
            .value
            .trim(),

        manOfTheMatch:
          manOfTheMatchSelect.value.trim(),

        playerPerformances:
          playerPerformancesInput.value.trim(),

        possession:
          document
            .getElementById("possession")
            .value
            .trim(),

        shots:
          document
            .getElementById("shots")
            .value
            .trim(),

        keyMoments:
          document
            .getElementById("keyMoments")
            .value
            .trim()
      };

      setLoadingState(true);

      reportOutput.innerHTML = `
        <div class="loading-state">
          <div class="spinner"></div>

          <h3>Analysing match...</h3>

          <p>
            Calculating player ratings,
            match intelligence and team badges.
          </p>
        </div>
      `;

      try {
        const response = await fetch(
          `${API_BASE_URL}/generate-report`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body: JSON.stringify(matchData)
          }
        );

        if (!response.ok) {
          const errorText =
            await response.text();

          throw new Error(
            `Backend returned ${response.status}: ${errorText}`
          );
        }

        const data =
          await response.json();

        renderPremiumDashboard(data, matchData);

        displayHistory(
          data.history
        );

        await displayMatchHeader(
          matchData.homeTeam,
          matchData.awayTeam,
          matchData.finalScore
        );

        reportSection.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });

      } catch (error) {
        console.error(error);

        reportOutput.innerHTML = `
          <div class="error-state">
            <h3>Something went wrong</h3>

            <p>
              Could not generate the report.
              Make sure the Python backend is
              running and the files were saved.
            </p>
          </div>
        `;

      } finally {
        setLoadingState(false);
      }
    }
  );


async function loadSquad(
  teamName,
  side
) {
  if (!teamName) {
    showSquadStatus(
      `Enter the ${side} team name first.`,
      "error"
    );

    return;
  }

  const button =
    side === "home"
      ? loadHomeSquadButton
      : loadAwaySquadButton;

  const originalText =
    button.textContent;

  button.disabled = true;
  button.textContent = "Loading...";

  showSquadStatus(
    `Loading ${teamName} squad...`,
    "loading"
  );

  try {
    const response = await fetch(
      `${API_BASE_URL}/load-squad`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          teamName: teamName,
          competitionCode: "PL"
        })
      }
    );

    const data =
      await response.json();

    if (!response.ok) {
      const message =
        data.detail
        || "Could not load the squad.";

      throw new Error(message);
    }

    const formattedSquad =
      data.squad.map(function (player) {
        return {
          id: player.id,
          name: player.name,
          position: player.position,
          nationality:
            player.nationality,
          team:
            data.team.shortName
            || data.team.name,
          side: side
        };
      });

    if (side === "home") {
      homeSquad = formattedSquad;

      homeSquadHeader.textContent =
        `${data.team.shortName || data.team.name} squad`;

      renderSquad(
        homeSquad,
        homeSquadList
      );

    } else {
      awaySquad = formattedSquad;

      awaySquadHeader.textContent =
        `${data.team.shortName || data.team.name} squad`;

      renderSquad(
        awaySquad,
        awaySquadList
      );
    }

    squadSelectionSection.classList.remove(
      "hidden"
    );

    showSquadStatus(
      `${data.playerCount} players loaded for ${
        data.team.shortName
        || data.team.name
      }.`,
      "success"
    );

  } catch (error) {
    console.error(error);

    showSquadStatus(
      error.message,
      "error"
    );

  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}


function renderSquad(
  squad,
  container
) {
  if (!squad.length) {
    container.innerHTML = `
      <p class="muted">
        No players were returned.
      </p>
    `;

    return;
  }

  container.innerHTML =
    squad
      .map(function (player) {
        const playerKey =
          createPlayerKey(player);

        const isSelected =
          selectedPlayers.some(
            function (selectedPlayer) {
              return (
                createPlayerKey(
                  selectedPlayer
                )
                === playerKey
              );
            }
          );

        return `
          <label class="squad-player-option">
            <input
              type="checkbox"
              class="player-checkbox"
              data-player-id="${escapeHtml(
                player.id
              )}"
              data-player-name="${escapeHtml(
                player.name
              )}"
              data-player-position="${escapeHtml(
                player.position
              )}"
              data-player-nationality="${escapeHtml(
                player.nationality
              )}"
              data-player-team="${escapeHtml(
                player.team
              )}"
              data-player-side="${escapeHtml(
                player.side
              )}"
              ${isSelected ? "checked" : ""}
            />

            <span class="player-option-content">
              <strong>
                ${escapeHtml(player.name)}
              </strong>

              <small>
                ${escapeHtml(
                  player.position
                )}
                ·
                ${escapeHtml(
                  player.nationality
                )}
              </small>
            </span>
          </label>
        `;
      })
      .join("");

  container
    .querySelectorAll(
      ".player-checkbox"
    )
    .forEach(function (checkbox) {
      checkbox.addEventListener(
        "change",
        handlePlayerSelection
      );
    });
}


function handlePlayerSelection(event) {
  const checkbox =
    event.target;

  const player = {
    id: checkbox.dataset.playerId,
    name: checkbox.dataset.playerName,
    position:
      checkbox.dataset.playerPosition,
    nationality:
      checkbox.dataset.playerNationality,
    team: checkbox.dataset.playerTeam,
    side: checkbox.dataset.playerSide,
    stats: createDefaultStats(
      checkbox.dataset.playerPosition
    )
  };

  const playerKey =
    createPlayerKey(player);

  if (checkbox.checked) {
    const alreadySelected =
      selectedPlayers.some(
        function (selectedPlayer) {
          return (
            createPlayerKey(
              selectedPlayer
            )
            === playerKey
          );
        }
      );

    if (!alreadySelected) {
      selectedPlayers.push(player);
    }

  } else {
    selectedPlayers =
      selectedPlayers.filter(
        function (selectedPlayer) {
          return (
            createPlayerKey(
              selectedPlayer
            )
            !== playerKey
          );
        }
      );
  }

  renderSelectedPlayers();
}


function createPlayerKey(player) {
  return [
    player.side,
    player.id || player.name
  ].join("-");
}



function normalisePosition(position) {
  const cleanPosition = String(position || "").trim().toLowerCase();

  if (cleanPosition.includes("goalkeeper") || cleanPosition === "gk") {
    return "Goalkeeper";
  }

  if (cleanPosition.includes("defence") || cleanPosition.includes("defender")) {
    return "Defence";
  }

  if (cleanPosition.includes("midfield") || cleanPosition.includes("midfielder")) {
    return "Midfield";
  }

  if (
    cleanPosition.includes("offence")
    || cleanPosition.includes("forward")
    || cleanPosition.includes("striker")
    || cleanPosition.includes("winger")
  ) {
    return "Offence";
  }

  return "Unknown";
}


function getPositionStatDefinitions(position) {
  const definitions = {
    Goalkeeper: [
      { key: "saves", label: "Saves", type: "number" },
      { key: "goalsConceded", label: "Goals conceded", type: "number" },
      { key: "penaltySaves", label: "Penalty saves", type: "number" },
      { key: "cleanSheet", label: "Clean sheet", type: "checkbox" }
    ],
    Defence: [
      { key: "goals", label: "Goals", type: "number" },
      { key: "assists", label: "Assists", type: "number" },
      { key: "tackles", label: "Tackles", type: "number" },
      { key: "interceptions", label: "Interceptions", type: "number" },
      { key: "clearances", label: "Clearances", type: "number" },
      { key: "defensiveErrors", label: "Errors", type: "number" },
      { key: "cleanSheet", label: "Clean sheet", type: "checkbox" }
    ],
    Midfield: [
      { key: "goals", label: "Goals", type: "number" },
      { key: "assists", label: "Assists", type: "number" },
      { key: "keyPasses", label: "Key passes", type: "number" },
      { key: "chancesCreated", label: "Chances created", type: "number" },
      { key: "tackles", label: "Tackles", type: "number" }
    ],
    Offence: [
      { key: "goals", label: "Goals", type: "number" },
      { key: "assists", label: "Assists", type: "number" },
      { key: "shots", label: "Shots", type: "number" },
      { key: "shotsOnTarget", label: "On target", type: "number" },
      { key: "bigChancesMissed", label: "Big chances missed", type: "number" }
    ],
    Unknown: [
      { key: "goals", label: "Goals", type: "number" },
      { key: "assists", label: "Assists", type: "number" },
      { key: "shots", label: "Shots", type: "number" },
      { key: "tackles", label: "Tackles", type: "number" }
    ]
  };

  return definitions[normalisePosition(position)] || definitions.Unknown;
}


function createDefaultStats(position) {
  const stats = {};

  getPositionStatDefinitions(position).forEach(function (definition) {
    stats[definition.key] = definition.type === "checkbox" ? false : 0;
  });

  return stats;
}


function createStatInput(player, definition) {
  const currentValue = player.stats[definition.key];

  if (definition.type === "checkbox") {
    return `
      <label class="player-checkbox-stat">
        <input
          type="checkbox"
          class="player-stat-input"
          data-stat="${escapeHtml(definition.key)}"
          ${currentValue ? "checked" : ""}
        />
        <span>${escapeHtml(definition.label)}</span>
      </label>
    `;
  }

  return `
    <label class="player-number-stat">
      <span>${escapeHtml(definition.label)}</span>
      <input
        type="number"
        min="0"
        step="1"
        value="${Number(currentValue) || 0}"
        class="player-stat-input"
        data-stat="${escapeHtml(definition.key)}"
        aria-label="${escapeHtml(player.name)} ${escapeHtml(definition.label)}"
      />
    </label>
  `;
}


function renderSelectedPlayers() {
  if (!selectedPlayers.length) {
    selectedPlayersSection.classList.add("hidden");
    selectedPlayersTable.innerHTML = "";
    updateManOfTheMatchOptions();
    playerPerformancesInput.value = "";
    return;
  }

  selectedPlayersSection.classList.remove("hidden");

  selectedPlayers.sort(function (firstPlayer, secondPlayer) {
    if (firstPlayer.side !== secondPlayer.side) {
      return firstPlayer.side === "home" ? -1 : 1;
    }
    return firstPlayer.name.localeCompare(secondPlayer.name);
  });

  selectedPlayersTable.innerHTML = selectedPlayers.map(function (player) {
    const key = createPlayerKey(player);

    if (!player.stats) {
      player.stats = createDefaultStats(player.position);
    }

    const statInputs = getPositionStatDefinitions(player.position)
      .map(function (definition) {
        return createStatInput(player, definition);
      })
      .join("");

    return `
      <article class="player-stat-card" data-player-key="${escapeHtml(key)}">
        <div class="player-stat-card-header">
          <div class="selected-player-name">
            <strong>${escapeHtml(player.name)}</strong>
            <small>
              ${escapeHtml(player.team)} · ${escapeHtml(normalisePosition(player.position))}
            </small>
          </div>

          <button
            type="button"
            class="remove-player-button"
            data-remove-player="${escapeHtml(key)}"
            aria-label="Remove ${escapeHtml(player.name)}"
          >×</button>
        </div>

        <div class="position-stat-grid">${statInputs}</div>
      </article>
    `;
  }).join("");

  selectedPlayersTable.querySelectorAll(".player-stat-input").forEach(function (input) {
    input.addEventListener(
      input.type === "checkbox" ? "change" : "input",
      handlePlayerStatChange
    );
  });

  selectedPlayersTable.querySelectorAll(".remove-player-button").forEach(function (button) {
    button.addEventListener("click", function () {
      removeSelectedPlayer(button.dataset.removePlayer);
    });
  });

  updateManOfTheMatchOptions();
  updateHiddenPlayerPerformances();
}


function handlePlayerStatChange(event) {
  const input = event.target;
  const card = input.closest(".player-stat-card");

  if (!card) {
    return;
  }

  const player = selectedPlayers.find(function (selectedPlayer) {
    return createPlayerKey(selectedPlayer) === card.dataset.playerKey;
  });

  if (!player) {
    return;
  }

  if (!player.stats) {
    player.stats = createDefaultStats(player.position);
  }

  player.stats[input.dataset.stat] = input.type === "checkbox"
    ? input.checked
    : Math.max(0, Number.parseInt(input.value, 10) || 0);

  updateHiddenPlayerPerformances();
}


function removeSelectedPlayer(
  playerKey
) {
  selectedPlayers =
    selectedPlayers.filter(
      function (player) {
        return (
          createPlayerKey(player)
          !== playerKey
        );
      }
    );

  document
    .querySelectorAll(
      ".player-checkbox"
    )
    .forEach(function (checkbox) {
      const checkboxKey = [
        checkbox.dataset.playerSide,
        checkbox.dataset.playerId
        || checkbox.dataset.playerName
      ].join("-");

      if (checkboxKey === playerKey) {
        checkbox.checked = false;
      }
    });

  renderSelectedPlayers();
}


function updateManOfTheMatchOptions() {
  const currentValue =
    manOfTheMatchSelect.value;

  manOfTheMatchSelect.innerHTML = `
    <option value="">
      Select a player
    </option>
  `;

  selectedPlayers.forEach(
    function (player) {
      const option =
        document.createElement(
          "option"
        );

      option.value = player.name;

      option.textContent =
        `${player.name} (${player.team})`;

      manOfTheMatchSelect.appendChild(
        option
      );
    }
  );

  const valueStillExists =
    selectedPlayers.some(
      function (player) {
        return (
          player.name
          === currentValue
        );
      }
    );

  if (valueStillExists) {
    manOfTheMatchSelect.value =
      currentValue;
  }
}


function updateHiddenPlayerPerformances() {
  const playerData = selectedPlayers.map(function (player) {
    return {
      name: player.name,
      position: normalisePosition(player.position),
      team: player.team,
      side: player.side,
      stats: player.stats || createDefaultStats(player.position)
    };
  });

  playerPerformancesInput.value = JSON.stringify(playerData);
}


function showSquadStatus(
  message,
  type
) {
  squadStatus.className =
    `status-message ${type}`;

  squadStatus.textContent =
    message;
}


function clearLoadingTimers() {
  loadingTimers.forEach(function (timer) {
    window.clearTimeout(timer);
  });
  loadingTimers = [];
}


function updateLoadingStage(percent, stage, message) {
  if (loadingProgress) loadingProgress.style.width = `${percent}%`;
  if (loadingPercent) loadingPercent.textContent = `${percent}%`;
  if (loadingStage) loadingStage.textContent = stage;
  if (loadingMessage) loadingMessage.textContent = message;
}


function showLoadingOverlay() {
  clearLoadingTimers();
  loadingStartedAt = Date.now();

  if (!loadingOverlay) return;

  loadingOverlay.classList.remove("hidden");
  loadingOverlay.classList.remove("is-closing");
  document.body.classList.add("is-loading");
  updateLoadingStage(8, "Stage 1 of 5", "Validating match information...");

  [
    [420, 28, "Stage 2 of 5", "Reading team statistics and the final score..."],
    [980, 49, "Stage 3 of 5", "Calculating position-aware player ratings..."],
    [1580, 70, "Stage 4 of 5", "Building tactical analysis and match intelligence..."],
    [2200, 88, "Stage 5 of 5", "Preparing the dashboard, badges and visualisations..."]
  ].forEach(function (stage) {
    loadingTimers.push(window.setTimeout(function () {
      updateLoadingStage(stage[1], stage[2], stage[3]);
    }, stage[0]));
  });
}


function hideLoadingOverlay() {
  clearLoadingTimers();
  if (!loadingOverlay) return;

  const elapsed = Date.now() - loadingStartedAt;
  const remainingDelay = Math.max(0, 900 - elapsed);

  window.setTimeout(function () {
    updateLoadingStage(100, "Analysis complete", "Your AI match dashboard is ready.");
    loadingOverlay.classList.add("is-closing");

    window.setTimeout(function () {
      loadingOverlay.classList.add("hidden");
      loadingOverlay.classList.remove("is-closing");
      document.body.classList.remove("is-loading");
      updateLoadingStage(8, "Stage 1 of 5", "Validating match information...");
    }, 340);
  }, remainingDelay);
}


function setLoadingState(isLoading) {
  generateButton.disabled = isLoading;
  generateButton.textContent = isLoading ? "Analysing..." : "Generate Report";
  if (isLoading) {
    downloadPdfButton?.classList.add("hidden");
    showLoadingOverlay();
  } else {
    hideLoadingOverlay();
  }
}


async function getTeamLogo(teamName) {
  try {
    const encodedTeamName =
      encodeURIComponent(teamName);

    const response = await fetch(
      `${API_BASE_URL}/team-logo/${encodedTeamName}`
    );

    if (!response.ok) {
      return null;
    }

    const data =
      await response.json();

    return data.logo || null;

  } catch (error) {
    console.error(
      `Could not load badge for ${teamName}:`,
      error
    );

    return null;
  }
}


function createTeamDisplay(
  teamName,
  logoUrl
) {
  const safeTeamName =
    escapeHtml(teamName);

  const badge = logoUrl
    ? `
      <img
        src="${logoUrl}"
        alt="${safeTeamName} badge"
      />

      <div
        class="logo-placeholder fallback-hidden"
      >
        ⚽
      </div>
    `
    : `
      <div class="logo-placeholder">
        ⚽
      </div>
    `;

  return `
    <div class="team-display">
      ${badge}

      <h3>${safeTeamName}</h3>
    </div>
  `;
}


async function displayMatchHeader(
  homeTeam,
  awayTeam,
  finalScore
) {
  matchHeader.classList.remove(
    "hidden"
  );

  matchHeader.innerHTML = `
    <div class="header-loading">
      Loading team badges...
    </div>
  `;

  const [homeLogo, awayLogo] =
    await Promise.all([
      getTeamLogo(homeTeam),
      getTeamLogo(awayTeam)
    ]);

  matchHeader.innerHTML = `
    ${createTeamDisplay(
      homeTeam,
      homeLogo
    )}

    <div class="score-display">
      <span class="score-label">
        Final score
      </span>

      <strong>
        ${escapeHtml(finalScore)}
      </strong>
    </div>

    ${createTeamDisplay(
      awayTeam,
      awayLogo
    )}
  `;

  matchHeader
    .querySelectorAll("img")
    .forEach(function (image) {
      image.addEventListener(
        "error",
        function () {
          image.style.display = "none";

          const fallback =
            image.nextElementSibling;

          if (fallback) {
            fallback.style.display =
              "grid";
          }
        }
      );
    });
}


async function loadHistory() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/history`
    );

    if (!response.ok) {
      throw new Error(
        "Could not load history."
      );
    }

    const data =
      await response.json();

    displayHistory(
      data.history
    );

  } catch (error) {
    console.error(error);

    historyOutput.innerHTML = `
      <p class="muted">
        Could not load match history.
        Start the backend and refresh.
      </p>
    `;
  }
}


function displayHistory(history) {
  if (
    !history
    || history.length === 0
  ) {
    historyOutput.innerHTML = `
      <p class="muted">
        No reports generated yet.
      </p>
    `;

    return;
  }

  historyOutput.innerHTML =
    history
      .map(function (match) {
        return `
          <article class="history-item">
            <div>
              <p class="history-date">
                ${escapeHtml(
                  match.createdAt
                )}
              </p>

              <h3>
                ${escapeHtml(
                  match.finalScore
                )}
              </h3>

              <div class="history-meta">
                <span>
                  ${escapeHtml(
                    match.matchType
                  )}
                </span>

                <span>
                  Winner:
                  ${escapeHtml(
                    match.winner
                  )}
                </span>

                <span>
                  Rating:
                  ${match.rating}/10
                </span>
              </div>
            </div>

            <button
              type="button"
              class="secondary-button history-report-button"
              data-match-id="${match.id}"
            >
              View Report
            </button>
          </article>
        `;
      })
      .join("");

  historyOutput
    .querySelectorAll(
      ".history-report-button"
    )
    .forEach(function (button) {
      button.addEventListener(
        "click",
        function () {
          showOldReport(
            Number(
              button.dataset.matchId
            )
          );
        }
      );
    });
}


async function showOldReport(matchId) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/history`
    );

    if (!response.ok) {
      throw new Error(
        "Could not retrieve history."
      );
    }

    const data =
      await response.json();

    const selectedMatch =
      data.history.find(
        function (match) {
          return match.id === matchId;
        }
      );

    if (!selectedMatch) {
      throw new Error(
        "Saved report was not found."
      );
    }

    dashboardOutput.classList.add("hidden");
    reportStatusBadge.classList.add("hidden");
    reportOutput.classList.remove("hidden");
    reportOutput.innerHTML =
      selectedMatch.report;

    await displayMatchHeader(
      selectedMatch.homeTeam,
      selectedMatch.awayTeam,
      selectedMatch.finalScore
    );

    reportOutput.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });

  } catch (error) {
    console.error(error);

    reportOutput.innerHTML = `
      <div class="error-state">
        <h3>Could not open report</h3>

        <p>
          The saved report could not
          be retrieved.
        </p>
      </div>
    `;
  }
}


function escapeHtml(value) {
  const element =
    document.createElement("div");

  element.textContent =
    String(value ?? "");

  return element.innerHTML;
}


function renderPremiumDashboard(data, matchData) {
  const reportSections = parseReportSections(data.report || "");
  const scoreData = parseScore(matchData.finalScore, matchData.homeTeam, matchData.awayTeam);
  const possessionData = parseTeamStat(matchData.possession);
  const shotsData = parseTeamStat(matchData.shots);
  const intelligence = extractIntelligence(data.report || "");
  const rating = Number(data.analysis?.rating ?? extractRating(data.report || ""));
  const structuredAnalysis = data.analysis || {};
  const confidence = structuredAnalysis.confidence || extractConfidence(data.report || "");
  const confidencePercent = Number(structuredAnalysis.confidencePercent) || confidenceToPercent(confidence);
  const winner = structuredAnalysis.winner || intelligence.Winner || scoreData.winner || "Draw";
  const resultType = structuredAnalysis.matchType || intelligence["Match Type"] || "Completed match";

  reportOutput.classList.add("hidden");
  dashboardOutput.classList.remove("hidden");
  reportStatusBadge.textContent = "AI Analysis Complete";
  reportStatusBadge.classList.remove("hidden");

  dashboardWinner.textContent = winner;
  dashboardResultType.textContent = resultType;
  dashboardConfidence.innerHTML = `${confidencePercent}%<small class="confidence-label">${escapeHtml(confidence || "Medium")}</small>`;
  animateMeter(confidenceMeter, confidencePercent);
  dashboardRating.textContent = `${rating.toFixed(1)}/10`;
  animateMeter(ratingMeter, Math.max(0, Math.min(100, rating * 10)));
  const motmName = matchData.manOfTheMatch || findMotm(data.playerRatings) || "Not selected";
  dashboardMotm.textContent = motmName;
  document.getElementById("motmOverviewCard")?.classList.toggle(
    "has-motm",
    motmName !== "Not selected"
  );

  comparisonHomeTeam.textContent = matchData.homeTeam || "Home";
  comparisonAwayTeam.textContent = matchData.awayTeam || "Away";
  comparisonRows.innerHTML = [
    createComparisonRow("Goals", scoreData.home, scoreData.away, scoreData.home, scoreData.away),
    createComparisonRow("Possession", possessionData.home, possessionData.away, possessionData.home, possessionData.away, "%"),
    createComparisonRow("Shots", shotsData.home, shotsData.away, shotsData.home, shotsData.away)
  ].join("");
  animateComparisonBars();

  dashboardSummary.innerHTML = reportSections["Match Summary"] ||
    `${escapeHtml(matchData.homeTeam)} faced ${escapeHtml(matchData.awayTeam)} in a match that finished ${escapeHtml(matchData.finalScore)}.`;

  const tacticalParts = [
    reportSections["Attacking Analysis"],
    reportSections["Possession Analysis"],
    reportSections["Tactical Verdict"]
  ].filter(Boolean);
  dashboardTactical.innerHTML = tacticalParts.length
    ? tacticalParts.join("")
    : "<p>No tactical analysis was returned.</p>";

  const keyMoments = splitKeyMoments(matchData.keyMoments || stripHtml(reportSections["Key Moments"] || ""));
  dashboardKeyMoments.innerHTML = keyMoments.length
    ? keyMoments.map(function (moment, index) {
        return `<li><span>${index + 1}</span><p>${escapeHtml(moment)}</p></li>`;
      }).join("")
    : '<li class="empty-list-item"><p>No key moments were provided.</p></li>';

  dashboardIndicators.innerHTML = [
    ["Match Type", resultType],
    ["Goal Difference", structuredAnalysis.goalDifference ?? intelligence["Goal Difference"] ?? Math.abs(scoreData.home - scoreData.away)],
    ["Shot Difference", structuredAnalysis.shotDifference ?? intelligence["Shot Difference"] ?? Math.abs(shotsData.home - shotsData.away)],
    ["Possession Gap", structuredAnalysis.possessionDifference !== undefined ? `${structuredAnalysis.possessionDifference}%` : intelligence["Possession Difference"] || `${Math.abs(possessionData.home - possessionData.away)}%`],
    ["Clean Sheet", structuredAnalysis.cleanSheet !== undefined ? (structuredAnalysis.cleanSheet ? "Yes" : "No") : intelligence["Clean Sheet"] || (scoreData.home === 0 || scoreData.away === 0 ? "Yes" : "No")],
    ["Goalscorers", matchData.goalscorers || "Not provided"]
  ].map(function (item) {
    return `<div class="indicator-card"><span>${escapeHtml(item[0])}</span><strong>${escapeHtml(item[1])}</strong></div>`;
  }).join("");

  dashboardVerdict.innerHTML = reportSections["Tactical Verdict"] ||
    reportSections["Key Insight"] ||
    "The report was generated successfully, but no final verdict was returned.";

  renderPremiumPlayerRatings(data.playerRatings || [], matchData.manOfTheMatch);
  renderPlayerRatingsChart(data.playerRatings || []);
  revealDashboard();
  downloadPdfButton?.classList.remove("hidden");
}

function parseReportSections(reportHtml) {
  const wrapper = document.createElement("div");
  wrapper.innerHTML = reportHtml;
  const sections = {};
  let currentHeading = null;

  Array.from(wrapper.children).forEach(function (node) {
    if (/^H[1-6]$/.test(node.tagName)) {
      currentHeading = node.textContent.trim();
      sections[currentHeading] = "";
      return;
    }
    if (currentHeading) sections[currentHeading] += node.outerHTML;
  });

  return sections;
}

function extractIntelligence(reportHtml) {
  const wrapper = document.createElement("div");
  wrapper.innerHTML = reportHtml;
  const intelligence = {};

  wrapper.querySelectorAll(".intelligence-grid > div").forEach(function (card) {
    const label = card.querySelector("span")?.textContent.trim();
    const value = card.querySelector("strong")?.textContent.trim();
    if (label && value) intelligence[label] = value;
  });

  return intelligence;
}

function extractRating(reportHtml) {
  const text = stripHtml(reportHtml);
  const match = text.match(/([0-9]+(?:\.[0-9]+)?)\s*\/\s*10/);
  return match ? Number(match[1]) : 0;
}

function extractConfidence(reportHtml) {
  const wrapper = document.createElement("div");
  wrapper.innerHTML = reportHtml;
  const heading = Array.from(wrapper.querySelectorAll("h3")).find(function (item) {
    return item.textContent.trim().toLowerCase() === "result confidence";
  });
  return heading?.nextElementSibling?.textContent.trim() || "Medium";
}

function confidenceToPercent(confidence) {
  const clean = String(confidence || "").toLowerCase();
  if (clean.includes("extremely")) return 94;
  if (clean.includes("high")) return 84;
  if (clean.includes("strong")) return 74;
  if (clean.includes("moderate")) return 64;
  if (clean.includes("even") || clean.includes("close")) return 50;
  return 60;
}

function parseScore(finalScore, homeTeam, awayTeam) {
  const scoreMatch = String(finalScore || "").match(/(\d+)\s*[-:]\s*(\d+)/);
  const home = scoreMatch ? Number(scoreMatch[1]) : 0;
  const away = scoreMatch ? Number(scoreMatch[2]) : 0;
  let winner = "Draw";
  if (home > away) winner = homeTeam || "Home";
  if (away > home) winner = awayTeam || "Away";
  return { home, away, winner };
}

function parseTeamStat(value) {
  const numbers = String(value || "").match(/\d+(?:\.\d+)?/g) || [];
  return { home: Number(numbers[0] || 0), away: Number(numbers[1] || 0) };
}

function createComparisonRow(label, homeDisplay, awayDisplay, homeValue, awayValue, suffix = "") {
  const total = Math.max(1, Number(homeValue) + Number(awayValue));
  const homeWidth = Math.max(4, (Number(homeValue) / total) * 100);
  const awayWidth = Math.max(4, (Number(awayValue) / total) * 100);

  return `
    <div class="comparison-row">
      <strong>${escapeHtml(homeDisplay)}${suffix}</strong>
      <div class="comparison-centre">
        <span>${escapeHtml(label)}</span>
        <div class="dual-bar">
          <i class="home-bar" data-bar-width="${homeWidth}"></i>
          <i class="away-bar" data-bar-width="${awayWidth}"></i>
        </div>
      </div>
      <strong>${escapeHtml(awayDisplay)}${suffix}</strong>
    </div>
  `;
}

function animateComparisonBars() {
  if (!comparisonRows) return;

  const bars = comparisonRows.querySelectorAll("[data-bar-width]");

  bars.forEach(function (bar) {
    bar.style.width = "0%";
  });

  requestAnimationFrame(function () {
    bars.forEach(function (bar, index) {
      window.setTimeout(function () {
        bar.style.width = `${bar.dataset.barWidth}%`;
      }, index * 70);
    });
  });
}


function splitKeyMoments(value) {
  return String(value || "")
    .split(/\n|;|\.(?:\s+|$)/)
    .map(function (item) { return item.trim(); })
    .filter(Boolean)
    .slice(0, 8);
}

function stripHtml(value) {
  const element = document.createElement("div");
  element.innerHTML = String(value || "");
  return element.textContent || element.innerText || "";
}

function findMotm(playerRatings) {
  if (!Array.isArray(playerRatings) || !playerRatings.length) return "";
  const motm = playerRatings.find(function (player) { return player.isMotm; });
  return motm?.name || [...playerRatings].sort(function (a, b) {
    return Number(b.rating) - Number(a.rating);
  })[0]?.name || "";
}

function renderPremiumPlayerRatings(playerRatings, selectedMotm) {
  if (!Array.isArray(playerRatings) || playerRatings.length === 0) {
    dashboardPlayerRatings.innerHTML = '<p class="muted">No player ratings were generated.</p>';
    playerCountBadge.textContent = "0 players";
    return;
  }

  const sortedPlayers = [...playerRatings].sort(function (a, b) {
    return Number(b.rating) - Number(a.rating);
  });

  playerCountBadge.textContent = `${sortedPlayers.length} player${sortedPlayers.length === 1 ? "" : "s"}`;
  dashboardPlayerRatings.innerHTML = sortedPlayers.map(function (player, index) {
    const isMotm = player.isMotm || player.name === selectedMotm || (index === 0 && Number(player.rating) === 10);
    const rating = Number(player.rating || 0);
    const ratingClass = getRatingClass(rating);
    const summary = player.summary || player.performanceSummary || "Performance rating calculated from the submitted match statistics.";

    return `
      <article class="premium-player-card ${ratingClass} ${isMotm ? "motm-card" : ""}" style="--card-delay:${Math.min(index * 45, 700)}ms">
        <div class="premium-player-topline">
          <div>
            <span class="position-pill">${escapeHtml(player.position || "Player")}</span>
            <h4>${escapeHtml(player.name || "Unknown player")}</h4>
            <small>${escapeHtml(player.team || "")}</small>
          </div>
          <div class="premium-rating ${ratingClass}">${rating.toFixed(1)}</div>
        </div>
        <p>${escapeHtml(summary)}</p>
        <div class="rating-progress"><span data-rating-width="${Math.max(0, Math.min(100, rating * 10))}"></span></div>
        ${isMotm ? '<span class="premium-motm-badge">★ Man of the Match</span>' : ""}
      </article>
    `;
  }).join("");

  requestAnimationFrame(function () {
    dashboardPlayerRatings.querySelectorAll("[data-rating-width]").forEach(function (bar) {
      bar.style.width = `${bar.dataset.ratingWidth}%`;
    });
  });
}

function getRatingClass(rating) {
  const score = Number(rating || 0);
  if (score >= 8.5) return "rating-excellent";
  if (score >= 7.0) return "rating-good";
  if (score >= 6.0) return "rating-average";
  return "rating-poor";
}

function animateMeter(element, percentage) {
  if (!element) return;
  element.style.width = "0%";
  requestAnimationFrame(function () {
    element.style.width = `${Math.max(0, Math.min(100, Number(percentage) || 0))}%`;
  });
}

function revealDashboard() {
  if (!dashboardOutput) return;

  dashboardOutput.classList.remove("is-visible");
  dashboardOutput.querySelectorAll("[data-reveal-order]").forEach(function (item) {
    const order = Number(item.dataset.revealOrder) || 1;
    item.style.setProperty("--reveal-delay", `${Math.min((order - 1) * 65, 650)}ms`);
  });

  void dashboardOutput.offsetWidth;

  requestAnimationFrame(function () {
    dashboardOutput.classList.add("is-visible");
  });
}

function renderPlayerRatingsChart(playerRatings) {
  if (!playerRatingsChartCanvas) return;

  const sortedPlayers = Array.isArray(playerRatings)
    ? [...playerRatings].sort(function (a, b) { return Number(b.rating) - Number(a.rating); })
    : [];

  if (!sortedPlayers.length || typeof Chart === "undefined") {
    if (chartFallback) chartFallback.classList.remove("hidden");
    return;
  }

  if (chartFallback) chartFallback.classList.add("hidden");
  if (playerRatingsChart) playerRatingsChart.destroy();

  const colours = sortedPlayers.map(function (player) {
    const rating = Number(player.rating || 0);
    if (rating >= 8.5) return "rgba(34, 197, 94, 0.85)";
    if (rating >= 7.0) return "rgba(96, 165, 250, 0.85)";
    if (rating >= 6.0) return "rgba(245, 158, 11, 0.85)";
    return "rgba(251, 113, 133, 0.85)";
  });

  playerRatingsChart = new Chart(playerRatingsChartCanvas, {
    type: "bar",
    data: {
      labels: sortedPlayers.map(function (player) { return player.name; }),
      datasets: [{
        label: "Player Rating",
        data: sortedPlayers.map(function (player) { return Number(player.rating || 0); }),
        backgroundColor: colours,
        borderColor: colours,
        borderWidth: 1,
        borderRadius: 7,
        barThickness: 18
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      animation: { duration: 900, easing: "easeOutQuart" },
      scales: {
        x: {
          min: 0,
          max: 10,
          ticks: { color: "#9fb0c8", stepSize: 1 },
          grid: { color: "rgba(159, 176, 200, 0.10)" }
        },
        y: {
          ticks: { color: "#dbe6f4", autoSkip: false },
          grid: { display: false }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (context) { return ` Rating: ${Number(context.raw).toFixed(1)}/10`; }
          }
        }
      }
    }
  });
}


function createPdfFilename() {
  const home = document.getElementById("homeTeam")?.value.trim() || "home";
  const away = document.getElementById("awayTeam")?.value.trim() || "away";
  const safeName = `${home}-vs-${away}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `${safeName || "match"}-ai-analysis.pdf`;
}


function waitForPdfImage(image) {
  if (image.complete) {
    return Promise.resolve();
  }

  return new Promise(function (resolve) {
    let finished = false;

    function finish() {
      if (finished) return;
      finished = true;
      resolve();
    }

    image.addEventListener("load", finish, { once: true });
    image.addEventListener("error", finish, { once: true });
    window.setTimeout(finish, 2500);
  });
}


async function waitForPdfAssets(root) {
  if (document.fonts && document.fonts.ready) {
    try {
      await document.fonts.ready;
    } catch (error) {
      console.warn("Font readiness check failed before PDF export:", error);
    }
  }

  const images = Array.from(root.querySelectorAll("img"));
  await Promise.all(images.map(waitForPdfImage));

  if (playerRatingsChart) {
    try {
      playerRatingsChart.stop();
      playerRatingsChart.update("none");
      playerRatingsChart.resize();
    } catch (error) {
      console.warn("Could not prepare the ratings chart for PDF export:", error);
    }
  }

  await new Promise(function (resolve) {
    requestAnimationFrame(function () {
      requestAnimationFrame(resolve);
    });
  });
}


async function downloadMatchReport() {
  if (!dashboardOutput || dashboardOutput.classList.contains("hidden")) {
    window.alert("Generate a match report before exporting a PDF.");
    return;
  }

  const originalText = downloadPdfButton.textContent;
  const originalTitle = document.title;

  downloadPdfButton.disabled = true;
  downloadPdfButton.textContent = "Preparing PDF...";

  try {
    await waitForPdfAssets(reportSection);

    document.body.classList.add("pdf-export-mode");
    document.title = createPdfFilename().replace(/\.pdf$/i, "");

    await new Promise(function (resolve) {
      requestAnimationFrame(function () {
        requestAnimationFrame(resolve);
      });
    });

    /*
      Browser-native printing is intentionally used here instead of
      html2pdf/html2canvas. The dashboard contains external team badges,
      a Chart.js canvas, CSS grids, gradients and a long report. Chromium's
      print renderer handles those reliably and keeps text sharp, while
      canvas-based PDF libraries can fail or produce incomplete pages.

      In the print window choose "Save to PDF" as the destination.
    */
    window.print();
  } catch (error) {
    console.error("Could not prepare PDF export:", error);
    window.alert(
      "The PDF export could not be prepared. Refresh the page, generate the report again, and retry."
    );
  } finally {
    document.title = originalTitle;
    document.body.classList.remove("pdf-export-mode");
    downloadPdfButton.disabled = false;
    downloadPdfButton.textContent = originalText;
  }
}


downloadPdfButton?.addEventListener("click", downloadMatchReport);

loadHistory();
