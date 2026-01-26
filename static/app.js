const params = new URLSearchParams(window.location.search);
const GAME_ID = params.get("game_id");

const q = id => document.getElementById(id);
const svg = q("mapSVG");
const SVG_NS = "http://www.w3.org/2000/svg";

const PLAYER_COLORS = [
  "#3498db",
  "#e74c3c",
  "#2ecc71",
  "#f1c40f",
  "#9b59b6",
  "#1abc9c"
];

function clearSVG() {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
}

function circle(x, y, r, fill, stroke = "#aaa", sw = 2) {
  const c = document.createElementNS(SVG_NS, "circle");
  c.setAttribute("cx", x);
  c.setAttribute("cy", y);
  c.setAttribute("r", r);
  c.setAttribute("fill", fill);
  c.setAttribute("stroke", stroke);
  c.setAttribute("stroke-width", sw);
  return c;
}

function text(x, y, txt, size = 12, color = "#fff") {
  const t = document.createElementNS(SVG_NS, "text");
  t.setAttribute("x", x);
  t.setAttribute("y", y);
  t.setAttribute("text-anchor", "middle");
  t.setAttribute("dominant-baseline", "middle");
  t.setAttribute("font-size", size);
  t.setAttribute("fill", color);
  t.textContent = txt;
  return t;
}

function drawSystem(sys, x, y, hasCombat) {
  const g = document.createElementNS(SVG_NS, "g");
  g._x = x;
  g._y = y;
  g._id = sys.id;

  const base = circle(
    x, y, 36,
    "#1e1e1e",
    hasCombat ? "#e74c3c" : "#777",
    hasCombat ? 4 : 2
  );

  const name = sys.planets[0]?.name || sys.id;
  const label = text(x, y + 52, name, 13, "#000");

  g.appendChild(base);
  g.appendChild(label);

  g.addEventListener("click", () => {
    q("moveFrom").value = sys.id;
    q("moveTo").value = sys.id;
  });

  svg.appendChild(g);
  return g;
}

function drawUnits(system, g, players) {
  let offsetX = -18;

  Object.entries(system.ships || {}).forEach(([playerName, units]) => {
    if (!units || units.length === 0) return;

    const pIndex = players.findIndex(p => p.name === playerName);
    const color = PLAYER_COLORS[pIndex % PLAYER_COLORS.length];

    const c = circle(
      g._x + offsetX,
      g._y,
      9,
      color,
      "#000",
      1
    );

    const t = text(
      g._x + offsetX,
      g._y,
      units.length,
      10,
      "#000"
    );

    svg.appendChild(c);
    svg.appendChild(t);

    offsetX += 20;
  });
}

async function loadState() {
  const res = await fetch(`/api/state?game_id=${GAME_ID}`);
  const data = await res.json();
  if (!data.ok) return;

  q("roundNum").textContent = data.round;

  // Players
  q("activePlayer").innerHTML = "";
  data.players.forEach(p => {
    const o = document.createElement("option");
    o.value = p.name;
    o.textContent = p.name;
    q("activePlayer").appendChild(o);
  });

  // Systems dropdowns
  q("moveFrom").innerHTML = "";
  q("moveTo").innerHTML = "";

  data.systems.forEach(s => {
    const name = s.planets[0]?.name || s.id;

    const o1 = document.createElement("option");
    o1.value = s.id;
    o1.textContent = name;

    const o2 = o1.cloneNode(true);

    q("moveFrom").appendChild(o1);
    q("moveTo").appendChild(o2);
  });

  // ---------- MAP ----------
  clearSVG();

  const cx = 450;
  const cy = 300;

  const mecatol = data.systems.find(s => s.id === "s_mec");
  const others = data.systems.filter(s => s.id !== "s_mec");

  const positions = {};

  if (mecatol) {
    positions[mecatol.id] = { x: cx, y: cy };
  }

  const r = 220;
  others.forEach((s, i) => {
    const a = (i / others.length) * Math.PI * 2;
    positions[s.id] = {
      x: cx + Math.cos(a) * r,
      y: cy + Math.sin(a) * r
    };
  });

  data.systems.forEach(sys => {
    const pos = positions[sys.id];
    const hasCombat =
      data.pending_combats &&
      data.pending_combats[sys.id];

    const g = drawSystem(sys, pos.x, pos.y, hasCombat);
    drawUnits(sys, g, data.players);
  });

  q("history").textContent =
    JSON.stringify(data.history, null, 2);
}

q("btnRefresh").onclick = loadState;

q("btnDoMove").onclick = async () => {
  const payload = {
    game_id: GAME_ID,
    player: q("activePlayer").value,
    action: {
      type: "move",
      from: q("moveFrom").value,
      to: q("moveTo").value
    }
  };

  await fetch("/api/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  loadState();
};

loadState();
