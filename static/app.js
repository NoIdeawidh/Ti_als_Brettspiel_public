// UI controller: keeps the local view in sync with the server state.

import { fetchState, fetchUnitTypes, sendAction } from "./api.js";
import { renderMap } from "./render.js";

const GAME_ID = new URLSearchParams(window.location.search).get("game_id");
const q = id => document.getElementById(id);

const view = {
  state: null,
  unitTypes: [],
  selectedSystem: null,
  selectedUnits: new Set()
};

function setStatus(message, kind = "muted") {
  const node = q("status");
  node.textContent = message;
  node.className = kind;
}

function fillSelect(select, options, keepValue = true) {
  const previous = select.value;
  select.innerHTML = "";
  options.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  if (keepValue && options.some(o => String(o.value) === previous)) {
    select.value = previous;
  }
}

function activePlayerName() {
  return q("activePlayer").value;
}

function systemsOf(player) {
  return view.state.systems.filter(s => (s.ships[player] || []).length);
}

function renderPlayerInfo() {
  const player = view.state.players.find(p => p.name === activePlayerName());
  if (!player) return;
  q("playerInfo").textContent =
    `${player.faction} · ${player.resources} Ressourcen · ${player.influence} Einfluss · ` +
    `${player.vp} SP${player.passed ? " · gepasst" : ""}`;
}

function renderUnitList() {
  const container = q("unitList");
  container.innerHTML = "";
  const system = view.state.systems.find(s => s.id === q("moveFrom").value);
  const units = system ? system.ships[activePlayerName()] || [] : [];
  if (!units.length) {
    container.textContent = "keine Einheiten";
    return;
  }
  units.forEach(unit => {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = unit.uid;
    box.checked = view.selectedUnits.has(unit.uid);
    box.onchange = () =>
      box.checked ? view.selectedUnits.add(unit.uid) : view.selectedUnits.delete(unit.uid);
    label.appendChild(box);
    label.append(` ${unit.type} (Bewegung ${unit.move}, Kapazität ${unit.capacity})`);
    container.appendChild(label);
  });
}

function renderControls() {
  const state = view.state;
  const player = activePlayerName();
  const isStrategy = state.phase === "strategy";

  q("strategyBox").style.display = isStrategy ? "block" : "none";
  q("actionBox").style.display = state.phase === "action" ? "block" : "none";

  fillSelect(
    q("strategyCard"),
    state.available_strategy_cards.map(c => ({
      value: c.id,
      label: `${c.id} – ${c.name}`
    }))
  );

  const systemOptions = state.systems.map(s => ({
    value: s.id,
    label: s.planets.length ? s.planets.map(p => p.name).join(" / ") : `Leerraum ${s.id}`
  }));
  fillSelect(q("moveFrom"), systemsOf(player).map(s => ({
    value: s.id,
    label: s.planets.length ? s.planets[0].name : `Leerraum ${s.id}`
  })));
  fillSelect(q("moveTo"), systemOptions);

  fillSelect(
    q("produceSystem"),
    state.systems
      .filter(s => s.planets.some(p => p.controller === player))
      .map(s => ({ value: s.id, label: s.planets[0].name }))
  );
  fillSelect(
    q("produceUnit"),
    view.unitTypes.map(u => ({ value: u.name, label: `${u.name} (${u.cost})` }))
  );

  const invadeOptions = [];
  systemsOf(player).forEach(system => {
    system.planets
      .filter(p => p.controller !== player)
      .forEach(p => invadeOptions.push({ value: `${system.id}|${p.name}`, label: p.name }));
  });
  fillSelect(q("invadePlanet"), invadeOptions);

  renderUnitList();
  renderPlayerInfo();
}

function renderHeader() {
  const { round, phase, turn, winner } = view.state;
  q("roundNum").textContent = round;
  q("phaseName").textContent = phase;
  q("turnInfo").textContent = winner
    ? `Spiel beendet – Sieger: ${winner}`
    : `Am Zug: ${turn.current_player || "-"} · Sprecher: ${turn.speaker}`;
}

async function refresh() {
  const state = await fetchState(GAME_ID);
  if (!state.ok) {
    setStatus(state.error || "Spiel nicht gefunden", "error");
    return;
  }
  view.state = state;
  view.selectedUnits = new Set();

  fillSelect(q("activePlayer"), state.players.map(p => ({ value: p.name, label: p.name })));
  if (state.turn.current_player && !q("activePlayer").dataset.locked) {
    q("activePlayer").value = state.turn.current_player;
  }

  renderHeader();
  renderControls();
  q("history").textContent = state.history.slice(-25).join("\n");
  renderMap(q("map"), state, {
    onSelect: id => {
      view.selectedSystem = id;
      if (systemsOf(activePlayerName()).some(s => s.id === id)) {
        q("moveFrom").value = id;
        renderUnitList();
      } else {
        q("moveTo").value = id;
      }
      renderMap(q("map"), view.state, { onSelect: () => {}, selectedId: id });
    },
    selectedId: view.selectedSystem
  });
}

async function act(action) {
  const result = await sendAction(GAME_ID, activePlayerName(), action);
  setStatus(result.msg || result.error || "", result.ok ? "success" : "error");
  await refresh();
}

q("btnRefresh").onclick = refresh;
q("activePlayer").onchange = () => {
  q("activePlayer").dataset.locked = "1";
  renderControls();
};
q("moveFrom").onchange = renderUnitList;

q("btnPickStrategy").onclick = () =>
  act({ type: "select_strategy", card_id: Number(q("strategyCard").value) });

q("btnDoMove").onclick = () =>
  act({
    type: "move",
    from: q("moveFrom").value,
    to: q("moveTo").value,
    units: view.selectedUnits.size ? [...view.selectedUnits] : null
  });

q("btnProduce").onclick = () =>
  act({ type: "produce", system: q("produceSystem").value, units: [q("produceUnit").value] });

q("btnInvade").onclick = () => {
  const [systemId, planet] = (q("invadePlanet").value || "").split("|");
  if (!systemId) return setStatus("Kein Planet auswählbar", "error");
  return act({ type: "invade", system: systemId, planet });
};

q("btnEndTurn").onclick = () => act({ type: "end_turn" });
q("btnPass").onclick = () => act({ type: "pass" });

(async function init() {
  const meta = await fetchUnitTypes();
  view.unitTypes = (meta.unit_types || []).filter(u => u.ship);
  await refresh();
})();
