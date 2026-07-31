# Twilight Imperium – digitale Umsetzung

Prototyp einer digitalen Umsetzung des Brettspiels *Twilight Imperium*:
Flask-Backend mit Spiellogik, statisches Frontend mit SVG-Hexkarte.

## Schnellstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python server.py           # http://127.0.0.1:5000
pytest                     # Tests
```

Lobby (`/`) → Spieler anlegen → *Create Game* → Spielansicht (`/game?game_id=...`).

## Architektur

| Modul | Verantwortung |
| --- | --- |
| `ti/hexmap.py` | Axiale Hex-Koordinaten, Nachbarschaft, Distanz, Ringe |
| `ti/units.py` | Einheitentypen (Kosten, Kampfwert, Bewegung, Kapazität) |
| `ti/cards.py` | Strategiekarten inkl. Initiative und Boni |
| `ti/models.py` | Domänenmodell (`Unit`, `Planet`, `System`, `Player`, `Board`) + Serialisierung |
| `ti/setup.py` | Galaxie- und Spieler-Setup |
| `ti/combat.py` | Würfelbasierter Raumkampf über mehrere Runden |
| `ti/engine.py` | Regelprüfung für Aktionen (Bewegung, Produktion, Invasion) |
| `ti/phases.py` | Rundenstruktur, Zugreihenfolge, Sprecher |
| `ti/game.py` | Aggregat: Aktionsdispatch, Statusphase, Siegbedingung |
| `ti/store.py` | Spielstände (In-Memory + JSON-Dateien in `saves/`) |
| `server.py` | HTTP-Schicht (nur Übersetzung JSON ↔ Engine) |
| `static/` | Frontend-Module: `api.js`, `hexmap.js`, `render.js`, `app.js` |

Die Wurzelmodule `game.py`, `engine.py`, `combat.py`, `cards.py` sind nur noch
Re-Exports für ältere Importe.

## Spielablauf

1. **Strategiephase** – jeder Spieler wählt in Sprecherreihenfolge eine Strategiekarte
   (Boni auf Ressourcen/Einfluss/Siegpunkte, Initiative bestimmt die Zugreihenfolge).
2. **Aktionsphase** – Züge in Initiativreihenfolge: `move`, `produce`, `invade`,
   `end_turn`, `pass`.
3. **Statusphase** – Einkommen aus kontrollierten Planeten, Siegpunkte
   (Mecatol Rex + Kartenbonus), Sprecher rotiert, neue Runde. Bei 10 Siegpunkten endet das Spiel.

Bewegung ist gültig, wenn die Hex-Distanz die kleinste Bewegungsreichweite der
bewegten Schiffe nicht übersteigt und genug Transportkapazität für Einheiten ohne
eigene Bewegung vorhanden ist. Treffen in einem System Flotten mehrerer Spieler
aufeinander, wird sofort ein Raumkampf ausgewürfelt (W10, Treffer ≤ Kampfwert,
günstigste Einheiten sterben zuerst).

## API

| Endpoint | Beschreibung |
| --- | --- |
| `POST /api/create` | `{players: [{name, faction, color}], seed?}` → `game_id` |
| `GET /api/state?game_id=` | Vollständiger Spielzustand |
| `POST /api/action` | `{game_id, player, action}` – siehe Aktionen oben |
| `POST /api/move` | Alias für `/api/action` (Altclients) |
| `GET /api/games` | Laufende und gespeicherte Spiele |
| `GET /api/unit_types`, `GET /api/strategy_cards` | Statische Regeldaten |

## Erweiterung

Neue Einheiten: Eintrag in `ti/units.py`. Neue Aktionen: Methode in `ti/engine.py`
plus Handler-Eintrag in `Game.apply_action`. Neue Karten/Hausregeln: `ti/cards.py`.
Der Spielzustand ist vollständig serialisierbar (`Game.to_dict`/`from_dict`), damit
bleiben Persistenz und späteres Netzwerkspiel unabhängig von der Regellogik.
