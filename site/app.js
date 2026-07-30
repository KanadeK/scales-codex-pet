"use strict";

const CELL_WIDTH = 192;
const CELL_HEIGHT = 208;
const ROWS = {
  "idle": { row: 0, frames: 6 },
  "running-right": { row: 1, frames: 8 },
  "running-left": { row: 2, frames: 8 },
  "waving": { row: 3, frames: 4 },
  "jumping": { row: 4, frames: 5 },
  "failed": { row: 5, frames: 8 },
  "waiting": { row: 6, frames: 6 },
  "running": { row: 7, frames: 6 },
  "review": { row: 8, frames: 6 },
};
const DIRECTION_NAMES = [
  "000", "022.5", "045", "067.5", "090", "112.5", "135", "157.5",
  "180", "202.5", "225", "247.5", "270", "292.5", "315", "337.5",
];

const canvas = document.querySelector("#pet-canvas");
const context = canvas.getContext("2d");
const statusNode = document.querySelector("#stage-status");
const stateSelect = document.querySelector("#state-select");
const directionSelect = document.querySelector("#direction-select");
const cellReadout = document.querySelector("#cell-readout");
const frameReadout = document.querySelector("#frame-readout");
const playButton = document.querySelector("#play-scenario");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

let atlas = null;
let currentState = "idle";
let currentFrame = 0;
let animationTimer = null;
let scenarioToken = 0;

function stopAnimation() {
  if (animationTimer !== null) {
    window.clearInterval(animationTimer);
    animationTimer = null;
  }
}

function drawCell(column, row, label, frameTotal = 1) {
  if (!atlas) {
    return;
  }
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(
    atlas,
    column * CELL_WIDTH,
    row * CELL_HEIGHT,
    CELL_WIDTH,
    CELL_HEIGHT,
    0,
    0,
    canvas.width,
    canvas.height,
  );
  cellReadout.textContent = `${column}, ${row}`;
  frameReadout.textContent = `${column + 1} of ${frameTotal}`;
  statusNode.textContent = label;
}

function startState(state, frameMs = 125) {
  scenarioToken += 1;
  stopAnimation();
  directionSelect.value = "";
  currentState = state;
  currentFrame = 0;
  stateSelect.value = state;
  const spec = ROWS[state];
  drawCell(currentFrame, spec.row, `${state} from the shipped atlas`, spec.frames);
  if (reducedMotion.matches) {
    statusNode.textContent = `${state}, motion reduced to one frame`;
    return;
  }
  animationTimer = window.setInterval(() => {
    currentFrame = (currentFrame + 1) % spec.frames;
    drawCell(currentFrame, spec.row, `${state} from the shipped atlas`, spec.frames);
  }, frameMs);
}

function lookAt(directionIndex) {
  scenarioToken += 1;
  stopAnimation();
  const column = directionIndex % 8;
  const row = 9 + Math.floor(directionIndex / 8);
  drawCell(column, row, `Looking ${DIRECTION_NAMES[directionIndex]} degrees`, 8);
}

function wait(ms, token) {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(token === scenarioToken), ms);
  });
}

async function playScenario() {
  const token = ++scenarioToken;
  stopAnimation();
  playButton.disabled = true;
  try {
    const response = await fetch("assets/scales-quest.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`scenario request returned ${response.status}`);
    }
    const scenario = await response.json();
    for (const event of scenario.events) {
      if (token !== scenarioToken) {
        return;
      }
      if (Object.hasOwn(event, "direction")) {
        const index = DIRECTION_NAMES.indexOf(String(event.direction).padStart(3, "0"));
        if (index < 0) {
          throw new Error(`unknown direction ${event.direction}`);
        }
        const column = index % 8;
        const row = 9 + Math.floor(index / 8);
        drawCell(column, row, `Scenario look ${DIRECTION_NAMES[index]} degrees`, 8);
        if (!(await wait(event.hold_ms || 600, token))) {
          return;
        }
        continue;
      }
      const aliases = { wake: "waving", "needs-input": "waiting", ready: "jumping" };
      const state = aliases[event.state] || event.state;
      const spec = ROWS[state];
      const loops = reducedMotion.matches ? 1 : (event.loops || 1);
      const frames = reducedMotion.matches ? 1 : spec.frames;
      for (let loop = 0; loop < loops; loop += 1) {
        for (let frame = 0; frame < frames; frame += 1) {
          drawCell(frame, spec.row, `Scenario state: ${state}`, spec.frames);
          if (!(await wait(event.frame_ms || 120, token))) {
            return;
          }
        }
      }
    }
    statusNode.textContent = "Scenario complete. Ready for review.";
  } catch (error) {
    statusNode.textContent = `Preview error: ${error.message}. Rebuild the site and verify assets.`;
  } finally {
    if (token === scenarioToken) {
      playButton.disabled = false;
    }
  }
}

stateSelect.addEventListener("change", () => startState(stateSelect.value));
directionSelect.addEventListener("change", () => {
  if (directionSelect.value === "") {
    startState(currentState);
  } else {
    lookAt(Number(directionSelect.value));
  }
});
playButton.addEventListener("click", playScenario);
reducedMotion.addEventListener("change", () => startState(currentState));

const image = new Image();
image.addEventListener("load", () => {
  if (image.naturalWidth !== 1536 || image.naturalHeight !== 2288) {
    statusNode.textContent =
      `Preview error: expected 1536 by 2288, received ${image.naturalWidth} by ${image.naturalHeight}.`;
    return;
  }
  atlas = image;
  startState("idle");
});
image.addEventListener("error", () => {
  statusNode.textContent =
    "Preview error: atlas could not load. Run python scripts/build_site.py and serve the output.";
});
image.src = "assets/spritesheet.webp";
