# Before

No airport simulator exists. The repo contains `calls.py`, a ~660-line discrete-event
simulator of a call center that uses `asimpy` (`Environment`, `Process`, `Interrupt`)
for events, `polars` for data, `altair` for plots, and `sqlalchemy` to write SQLite.
`CLAUDE.md` names `airport.py` as a planned file; it has not been created.

# After

Create `airport.py`, a single-file airport simulator matching `calls.py`'s structure
and conventions: no type annotations, short docstrings, named constants at the top,
imports at the top, minutes for all time math, datetimes in SQLite, durations in minutes.

Model:

- **Airlines** — 4, each with a code and name.
- **Flights** — `asimpy` `Process`. Each visits the airport once: arrives from an
  `origin`, turns around, departs to a `destination`. Carries scheduled and actual
  arrival/departure times, a seat `capacity`, and `arrival_delay_min` / `departure_delay_min`.
- **Passengers** — data, not processes. A passenger makes one short trip; flights are
  the repeating events. Three kinds:
  - `originating` — arrive directly, board a departure
  - `connecting` — arrive on one flight, board another
  - `terminating` — arrive on a flight, leave the airport
- **Seat limits** — enforced. A passenger who reaches a full flight is bumped to the
  next flight to the same destination and a `mishap` row is recorded.
- **Delays** — baseline small probability per flight; scenarios scale it.
- **Missed connections** — a connecting passenger whose inbound lands so late that
  `actual_arrival + MCT > departure` misses and is rebooked on the next flight to the
  same destination.

Decisions made:

- Passengers as data rather than `Process` — rejected per-passenger processes because
  a journey is one-shot, not repeating. [chosen]
- Seat limits enforced via bump-to-next-flight — rejected: treating capacity as a
  recorded attribute only (user explicitly asked for enforcement). [chosen]
- Scenarios `plain`, `weather`, `strike`, `rush`, `storm` — user-confirmed. [chosen]
- Name locale `en_CA` (Canadian English) — user-requested. [chosen]

Output:

- SQLite tables: `airline`, `flight`, `passenger`, `mishap`.
- Six `altair` plots per scenario, saved like `calls.py`.

Table shapes (simplified):

- `airline` — `airline_id`, `name`
- `flight` — `flight_id`, `airline_id`, `origin`, `destination`, `sched_arrival`,
  `actual_arrival`, `sched_departure`, `actual_departure`, `arrival_delay_min`,
  `departure_delay_min`, `capacity`
- `passenger` — `passenger_id`, `family`, `personal`, `kind`, `origin`, `destination`,
  `arrival_flight_id`, `departure_flight_id`, `arrived_at`, `departed_at`
- `mishap` — `mishap_id`, `passenger_id`, `missed_flight_id`, `rebooked_flight_id`,
  `missed_by_min`, `wait_min`

CLI: `--seed`, `--shock {plain,weather,strike,rush,storm}`.
