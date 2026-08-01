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
| `ti/objectives.py` | Öffentliche Ziele (Bedingung + Siegpunkte) |
| `ti/tech.py` | Technologien inkl. Voraussetzungen und Einheiten-Upgrades |
| `ti/anomalies.py` | Anomalien und Wurmlöcher (Bewegungs- und Kampfwirkung) |
| `ti/factions.py` | Fraktionen: Startboni, Starttechnologien, Kampfmodifikator |
| `ti/action_cards.py` | Aktionskarten (Effekt als Funktion über Spielzustand) |
| `ti/agenda.py` | Agenden (Gesetze/Direktiven), Abstimmung und Gesetzeswirkungen |
| `ti/models.py` | Domänenmodell (`Unit`, `Planet`, `System`, `Player`, `Board`) + Serialisierung |
| `ti/setup.py` | Galaxie- und Spieler-Setup |
| `ti/combat.py` | Würfelbasierter Raum- und Bodenkampf über mehrere Runden |
| `ti/engine.py` | Regelprüfung für Aktionen (Bewegung, Produktion, Invasion) |
| `ti/phases.py` | Rundenstruktur, Zugreihenfolge, Sprecher |
| `ti/game.py` | Aggregat: Aktionsdispatch, Statusphase, Siegbedingung |
| `ti/store.py` | Spielstände (In-Memory + JSON-Dateien in `saves/`) |
| `server.py` | HTTP-Schicht (nur Übersetzung JSON ↔ Engine) |
| `static/` | Frontend-Module: `api.js`, `hexmap.js`, `render.js`, `app.js` |

Die Wurzelmodule `game.py`, `engine.py`, `combat.py`, `cards.py` sind nur noch
Re-Exports für ältere Importe.

## Spielablauf

1. **Strategiephase** – jeder Spieler wählt in Sprecherreihenfolge eine Strategiekarte;
   die Initiative bestimmt die Zugreihenfolge. Die Karte wirkt erst, wenn sie
   ausgespielt wird.
2. **Aktionsphase** – Züge in Initiativreihenfolge: `play_strategy`, `follow`,
   `move`, `produce`, `build`, `research`, `invade`, `end_turn`, `pass`.
   `play_strategy` löst die Primärfähigkeit der eigenen Karte aus (einmal pro
   Runde), `follow` die schwächere Sekundärfähigkeit einer bereits ausgespielten
   fremden Karte – einmal pro Karte und Spieler und gegen ein Kommandotoken.
   **Handelsgüter** (Trade-Karte) sind eine zweite Währung: Sie zahlen, was die
   Ressourcen nicht decken, und lassen sich mit `trade` auch außerhalb des eigenen
   Zuges an Mitspieler abgeben, um Abkommen zu erfüllen. **Aktionskarten**
   (`play_action_card`) kommen aus einem gemeinsamen Stapel: jeder Spieler zieht
   in der Statusphase eine Karte (Handlimit 7), gespielte Karten wandern auf den
   Ablagestapel und werden bei leerem Deck neu gemischt.
   `move`, `produce`, `build` und `research` kosten ebenfalls je ein Kommandotoken
   (Start 3, +2 pro Runde, Leadership/Warfare geben zusätzliche, Maximum 8);
   ohne Token bleibt nur Zug beenden oder passen.
   Pro System darf ein Spieler höchstens so viele Nicht-Jäger-Schiffe halten, wie
   seine Flottenkapazität erlaubt (Start 4, Warfare primär +1); Jäger zählen nicht mit.
3. **Statusphase** – Einkommen aus kontrollierten Planeten, Wertung der
   aufgedeckten Ziele, Sprecher rotiert, ein neues Ziel wird aufgedeckt.
   Bei 10 Siegpunkten endet das Spiel.
4. **Agendaphase** – sobald Mecatol Rex einmal gehalten wurde: Eine Agenda wird
   aufgedeckt, jeder Spieler stimmt mit `vote` einmal ab (Einfluss wird
   ausgegeben), der Sprecher entscheidet Gleichstände. *Direktiven* wirken sofort,
   *Gesetze* bleiben liegen (`Game.laws`) und wirken über die Hilfsfunktionen in
   `ti/agenda.py` – z. B. höhere Forschungskosten oder ein niedrigeres
   Kommandotoken-Maximum.

Siegpunkte kommen aus **öffentlichen Zielen** (`ti/objectives.py`, ein Ziel pro
Runde aufgedeckt, jedes Ziel pro Spieler nur einmal wertbar), **geheimen Zielen**
(`SECRET_DECK`: jeder Spieler hält zwei, wertet höchstens eines pro Statusphase
und zieht danach nach), dem einmaligen Custodian-Bonus für den ersten Halter von
Mecatol Rex und Kartenboni.

**Bauwerke** (`build`) stehen auf einem kontrollierten Planeten, je Typ einmal:
Ein *Space Dock* erhöht die Produktionskapazität des Systems um 3, eine *PDS*
feuert vor dem Bodenkampf auf die landenden Truppen. Bei Verlust des Planeten
werden die Bauwerke zerstört.

**Technologien** (`ti/tech.py`) haben eine Farbe, Kosten und Voraussetzungen der
Form „mindestens N Technologien der Farbe X“. Einheiten-Upgrades sind eigene
`UnitType`-Einträge (`Carrier II`, `Cruiser II`, …) mit `base_type`: Beim
Erforschen werden alle vorhandenen Einheiten des Basistyps ersetzt, neue
Produktion und Bauwerke verwenden automatisch die verbesserte Variante.

Bewegung ist gültig, wenn die Hex-Distanz die kleinste Bewegungsreichweite der
bewegten Schiffe nicht übersteigt und genug Transportkapazität für Einheiten ohne
eigene Bewegung vorhanden ist. Treffen in einem System Flotten mehrerer Spieler
aufeinander, wird sofort ein Raumkampf ausgewürfelt (W10, Treffer ≤ Kampfwert,
günstigste Einheiten sterben zuerst).

Planeten haben Bodentruppen (`Planet.ground_forces`): Heimatplaneten starten mit
zwei Infanterie, neutrale Planeten mit bis zu zwei, Mecatol Rex mit drei. Eine
Invasion setzt Raumkontrolle voraus und landet transportierte Infanterie; der
Bodenkampf läuft nach denselben Würfelregeln. Überlebende Angreifer besetzen den
Planeten, bei Misserfolg kehren sie an Bord zurück.

## API

| Endpoint | Beschreibung |
| --- | --- |
| `POST /api/create` | `{players: [{name, faction, color}], seed?}` → `game_id` |
| `GET /api/state?game_id=` | Vollständiger Spielzustand |
| `GET /api/state?game_id=&since=` | Nur geänderte Zustände; bei gleicher `version` kommt `{ok, unchanged, version}` |
| `GET /api/state?game_id=&player=` | Spielersicht: fremde Handkarten, geheime Ziele und verdeckte Stapel sind nur als Anzahl enthalten |
| `POST /api/action` | `{game_id, player, action}` – siehe Aktionen oben |
| `POST /api/move` | Alias für `/api/action` (Altclients) |
| `GET /api/games` | Laufende und gespeicherte Spiele |
| `GET /api/unit_types`, `GET /api/strategy_cards` | Statische Regeldaten |

## Erweiterung

Neue Einheiten: Eintrag in `ti/units.py`. Neue Aktionen: Methode in `ti/engine.py`
plus Handler-Eintrag in `Game.apply_action`. Neue Karten/Hausregeln: `ti/cards.py`.
Der Spielzustand ist vollständig serialisierbar (`Game.to_dict`/`from_dict`), damit
bleiben Persistenz und späteres Netzwerkspiel unabhängig von der Regellogik.
