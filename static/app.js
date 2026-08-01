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
    `${player.faction} · ${player.resources} Ressourcen · ${player.trade_goods} Handelsgüter · ${player.influence} Einfluss · ` +
    `${player.command_tokens} Kommandotokens · Flotte ${player.fleet_supply} · ${player.vp} SP` +
    `${player.passed ? " · gepasst" : ""}` +
    `${player.technologies.length ? " · Tech: " + player.technologies.length : ""}`;
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

  renderStrategyActions();
  renderActionCards();
  fillSelect(
    q("tradePartner"),
    state.players.filter(p => p.name !== player).map(p => ({ value: p.name, label: p.name }))
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
    view.unitTypes
      .filter(u => !u.structure && !u.base_type)
      .map(u => ({ value: u.name, label: `${u.name} (${u.cost})` }))
  );

  const buildOptions = [];
  state.systems.forEach(system => {
    system.planets
      .filter(p => p.controller === player)
      .forEach(p =>
        buildOptions.push({
          value: `${system.id}|${p.name}`,
          label: `${p.name}${(p.structures || []).length ? " · " + p.structures.map(s => s.type).join(", ") : ""}`
        })
      );
  });
  fillSelect(q("buildPlanet"), buildOptions);
  fillSelect(
    q("buildStructure"),
    view.unitTypes
      .filter(u => u.structure && !u.base_type)
      .map(u => ({ value: u.name, label: `${u.name} (${u.cost})` }))
  );

  const owner = state.players.find(p => p.name === player);
  const known = new Set((owner && owner.technologies) || []);
  fillSelect(
    q("techSelect"),
    (state.technologies || [])
      .filter(t => !known.has(t.id))
      .map(t => ({
        value: t.id,
        label: `${t.name} (${t.cost}, ${t.color})`
      }))
  );

  const invadeOptions = [];
  systemsOf(player).forEach(system => {
    const troops = (system.ships[player] || []).filter(u => !u.ship).length;
    system.planets
      .filter(p => p.controller !== player)
      .forEach(p =>
        invadeOptions.push({
          value: `${system.id}|${p.name}`,
          label: `${p.name} (Garnison ${(p.ground_forces || []).length}, gelandet ${troops})`
        })
      );
  });
  fillSelect(q("invadePlanet"), invadeOptions);

  renderUnitList();
  renderPlayerInfo();
  renderObjectives();
  renderAgenda();
}

function renderActionCards() {
  const state = view.state;
  const owner = state.players.find(p => p.name === activePlayerName());
  const catalogue = state.action_cards || {};
  fillSelect(
    q("actionCard"),
    ((owner && owner.action_cards) || [])
      .filter(id => catalogue[id])
      .map(id => ({
        value: id,
        label: `${catalogue[id].name}: ${catalogue[id].desc}`
      }))
  );
  fillSelect(
    q("actionCardTarget"),
    state.players
      .filter(p => p.name !== activePlayerName())
      .map(p => ({ value: p.name, label: p.name }))
  );
  q("btnPlayActionCard").disabled = !q("actionCard").options.length;
}

function renderStrategyActions() {
  const state = view.state;
  const player = state.players.find(p => p.name === activePlayerName());
  const cards = state.strategy_cards || {};
  const card = player && player.strategy_card ? cards[player.strategy_card] : null;
  const played = state.played_cards || [];

  q("btnPlayStrategy").disabled = !card || played.includes(card.id);
  q("btnPlayStrategy").textContent = card
    ? `${card.name} ausspielen (${describeEffect(card.primary)})`
    : "Keine Strategiekarte";

  const followable = played
    .filter(id => cards[id] && (!player || player.strategy_card !== id))
    .filter(id => !(state.followers[id] || []).includes(activePlayerName()))
    .map(id => ({
      value: id,
      label: `${cards[id].name}: ${describeEffect(cards[id].secondary)}`
    }));
  fillSelect(q("followCard"), followable);
  q("btnFollow").disabled = !followable.length;
}

function describeEffect(effect) {
  const parts = [];
  if (effect.resources) parts.push(`${effect.resources} Ressourcen`);
  if (effect.influence) parts.push(`${effect.influence} Einfluss`);
  if (effect.tokens) parts.push(`${effect.tokens} Token`);
  if (effect.vp) parts.push(`${effect.vp} SP`);
  if (effect.trade_goods) parts.push(`${effect.trade_goods} Handelsgüter`);
  if (effect.action_cards) parts.push(`${effect.action_cards} Aktionskarten`);
  if (effect.free_research) parts.push(`${effect.free_research} freie Forschung`);
  if (effect.fleet_supply) parts.push(`${effect.fleet_supply} Flottenkapazität`);
  return parts.join(", ") || "kein Effekt";
}

function renderAgenda() {
  const state = view.state;
  const agenda = state.agenda;
  q("agendaBox").style.display = agenda ? "block" : "none";
  if (agenda) {
    const voted = Object.entries(agenda.votes)
      .map(([name, vote]) => `${name}: ${vote.influence} für ${vote.outcome}`)
      .join(", ");
    q("agendaInfo").textContent =
      `${agenda.name} (${agenda.kind}): ${agenda.desc}` +
      (voted ? ` – ${voted}` : "");
    fillSelect(
      q("agendaOutcome"),
      agenda.outcomes.map(o => ({ value: o, label: o }))
    );
  }

  const laws = Object.entries(state.laws || {});
  q("laws").textContent = laws.length
    ? laws.map(([id, outcome]) => `${id}: ${outcome}`).join(", ")
    : "keine Gesetze in Kraft";
}

function renderObjectives() {
  const container = q("objectives");
  container.innerHTML = "";
  (view.state.objectives || []).forEach(objective => {
    const line = document.createElement("div");
    const scorers = objective.scored_by.length ? ` – erfüllt: ${objective.scored_by.join(", ")}` : "";
    line.textContent = `${objective.name} (${objective.vp} SP): ${objective.desc}${scorers}`;
    container.appendChild(line);
  });
  if (!container.childElementCount) container.textContent = "keine Ziele aufgedeckt";
  renderSecrets();
}

function renderSecrets() {
  const container = q("secrets");
  container.innerHTML = "";
  const player = view.state.players.find(p => p.name === activePlayerName());
  const catalogue = view.state.secret_objectives || {};
  if (!player) return;
  player.secret_objectives.forEach(id => {
    const objective = catalogue[id];
    if (!objective) return;
    const line = document.createElement("div");
    line.textContent = `${objective.name} (${objective.vp} SP): ${objective.desc}`;
    container.appendChild(line);
  });
  player.scored_secrets.forEach(id => {
    const objective = catalogue[id];
    if (!objective) return;
    const line = document.createElement("div");
    line.textContent = `${objective.name} – erfüllt`;
    container.appendChild(line);
  });
  if (!container.childElementCount) container.textContent = "keine geheimen Ziele";
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
  const state = await fetchState(GAME_ID, q("activePlayer").value);
  if (!state.ok) {
    setStatus(state.error || "Spiel nicht gefunden", "error");
    return;
  }
  view.state = state;
  view.selectedUnits = new Set();

  fillSelect(
    q("activePlayer"),
    state.players.map(p => ({
      value: p.name,
      label: p.hidden_action_cards === undefined
        ? p.name
        : `${p.name} (${p.hidden_action_cards} Karten verdeckt)`
    }))
  );
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
  refresh();
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

q("btnBuild").onclick = () => {
  const [systemId, planet] = (q("buildPlanet").value || "").split("|");
  if (!systemId) return setStatus("Kein eigener Planet verfügbar", "error");
  return act({
    type: "build",
    system: systemId,
    planet,
    structure: q("buildStructure").value
  });
};

q("btnPlayStrategy").onclick = () => act({ type: "play_strategy" });

q("btnPlayActionCard").onclick = () =>
  act({
    type: "play_action_card",
    card: q("actionCard").value,
    target: q("actionCardTarget").value
  });

q("btnTrade").onclick = () =>
  act({
    type: "trade",
    partner: q("tradePartner").value,
    trade_goods: Number(q("tradeAmount").value)
  });

q("btnFollow").onclick = () =>
  act({ type: "follow", card_id: Number(q("followCard").value) });

q("btnVote").onclick = () =>
  act({
    type: "vote",
    outcome: q("agendaOutcome").value,
    influence: Number(q("agendaInfluence").value)
  });

q("btnResearch").onclick = () =>
  act({ type: "research", technology: q("techSelect").value });

q("btnInvade").onclick = () => {
  const [systemId, planet] = (q("invadePlanet").value || "").split("|");
  if (!systemId) return setStatus("Kein Planet auswählbar", "error");
  return act({ type: "invade", system: systemId, planet });
};

q("btnEndTurn").onclick = () => act({ type: "end_turn" });
q("btnPass").onclick = () => act({ type: "pass" });

(async function init() {
  const meta = await fetchUnitTypes();
  view.unitTypes = meta.unit_types || [];
  await refresh();
})();
