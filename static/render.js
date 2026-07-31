// SVG rendering of the galaxy map.

import { boundingBox, hexCorners, hexToPixel, HEX_SIZE } from "./hexmap.js";

const SVG_NS = "http://www.w3.org/2000/svg";

function el(name, attrs = {}) {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  return node;
}

function text(x, y, content, size, color) {
  const node = el("text", {
    x,
    y,
    "text-anchor": "middle",
    "dominant-baseline": "middle",
    "font-size": size,
    fill: color
  });
  node.textContent = content;
  return node;
}

function colorOf(players, name) {
  const player = players.find(p => p.name === name);
  return player ? player.color : "#888";
}

function drawSystem(svg, system, state, onSelect, selectedId) {
  const center = hexToPixel(system.hex);
  const group = el("g", { style: "cursor:pointer" });
  const owners = Object.entries(system.ships || {}).filter(([, u]) => u.length);
  const contested = owners.length > 1;

  group.appendChild(
    el("polygon", {
      points: hexCorners(center).map(p => p.join(",")).join(" "),
      fill: system.planets.length ? "#16213a" : "#0c101c",
      stroke: selectedId === system.id ? "#f1c40f" : contested ? "#e74c3c" : "#33415c",
      "stroke-width": selectedId === system.id ? 4 : 2
    })
  );

  system.planets.forEach((planet, index) => {
    const y = center.y - 10 + index * 22;
    group.appendChild(
      el("circle", {
        cx: center.x,
        cy: y,
        r: 13,
        fill: planet.controller ? colorOf(state.players, planet.controller) : "#5b6b8a",
        stroke: planet.home ? "#f1c40f" : "#0b0f18",
        "stroke-width": planet.home ? 3 : 1
      })
    );
    group.appendChild(text(center.x, y + 26, planet.name, 9, "#c8d6e8"));
    const garrison = (planet.ground_forces || []).length;
    if (garrison) {
      group.appendChild(
        el("rect", {
          x: center.x + 12,
          y: y - 8,
          width: 16,
          height: 14,
          rx: 3,
          fill: "#0b0f18",
          stroke: "#5b6b8a"
        })
      );
      group.appendChild(text(center.x + 20, y, String(garrison), 9, "#e6edf3"));
    }
    (planet.structures || []).forEach((structure, i) => {
      group.appendChild(
        text(center.x - 18 - i * 10, y, structure.type === "PDS" ? "⌂" : "⚒", 11, "#f1c40f")
      );
    });
  });

  if (!system.planets.length) {
    group.appendChild(text(center.x, center.y, "∅", 14, "#33415c"));
  }

  owners.forEach(([playerName, units], index) => {
    const x = center.x - 20 + index * 26;
    const y = center.y + HEX_SIZE * 0.62;
    group.appendChild(
      el("circle", { cx: x, cy: y, r: 10, fill: colorOf(state.players, playerName), stroke: "#000" })
    );
    group.appendChild(text(x, y, String(units.length), 10, "#0b0f18"));
  });

  group.addEventListener("click", () => onSelect(system.id));
  svg.appendChild(group);
}

export function renderMap(svg, state, { onSelect, selectedId }) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  if (!state.systems.length) return;

  const box = boundingBox(state.systems);
  svg.setAttribute("viewBox", `${box.minX} ${box.minY} ${box.width} ${box.height}`);
  state.systems.forEach(system => drawSystem(svg, system, state, onSelect, selectedId));
}
