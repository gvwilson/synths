#!/usr/bin/env python

"""Airport discrete event simulation."""

import altair as alt
import argparse
from asimpy import Environment, Process
from datetime import datetime, timedelta
from faker import Faker
import numpy as np
from pathlib import Path
import polars as pl
from sqlalchemy import create_engine

# Default random number generation seed.
SEED = 400582

# Locale for personal names.
LOCALE = "en_CA"

# Number of airlines and length of simulation.
NUM_DAYS = 7
FLIGHTS_PER_AIRLINE_PER_DAY = 6

# Start time and simulation duration.
SIMULATION_START = datetime(2025, 2, 3, 0, 0)
MINUTES_PER_DAY = 24 * 60
SIMULATION_TIME = NUM_DAYS * MINUTES_PER_DAY
RUN_OVERRUN = 480  # minutes past the end so delayed tail flights still depart

# The airport being simulated, the cities it connects to, and the airlines.
HUB_CITY = "Winnipeg"
CITIES = [
    "Toronto",
    "Vancouver",
    "Calgary",
    "Montreal",
    "Ottawa",
    "Halifax",
    "Edmonton",
    "Saskatoon",
]
AIRLINES = [
    ("AC", "Air Canada"),
    ("WS", "WestJet"),
    ("PD", "Porter Airlines"),
    ("TS", "Air Transat"),
]

# Range of turnaround time between a flight's arrival and departure (minutes).
TURNAROUND_MIN = 45
TURNAROUND_MAX = 90

# Baseline delay behaviour (probability and magnitude in minutes).
DELAY_PROBABILITY = 0.15
DELAY_MIN = 10
DELAY_MAX = 60

# Range of seat capacity per flight.
SEATS_MIN = 100
SEATS_MAX = 200

# Minimum time a connecting passenger needs to change flights (minutes).
MINIMUM_CONNECTION_TIME = 30
CONNECTION_WINDOW = 180  # how far after arrival a connection may depart

# Number of passengers of each kind per flight.
ORIGINATING_MIN = 40
ORIGINATING_MAX = 90
TERMINATING_MIN = 20
TERMINATING_MAX = 50
CONNECTING_MIN = 20
CONNECTING_MAX = 60

# How early before departure an originating passenger checks in (minutes).
CHECKIN_MIN = 60
CHECKIN_MAX = 150

# Shock parameters.
WEATHER_DELAY_PROBABILITY = 0.6
WEATHER_DELAY_MAX = 120
STRIKE_DELAY_MIN = 60
STRIKE_DELAY_MAX = 180
STORM_DURATION = 240
RUSH_EXTRA_MIN = 20
RUSH_EXTRA_MAX = 50

# Display properties.
PLOT_WIDTH = 450

# ----------------------------------------------------------------------


def main():
    args = parse_args()

    world = World(args.seed, args.shock)
    airlines = make_airlines(world)
    flights = make_flights(world)
    world.passengers = make_passengers(world, flights)

    simulate(world, flights)
    airlines, records = post_process(world, airlines)
    output_dir = Path(args.out)
    make_db(output_dir, args.shock, airlines, records)
    plot_all(output_dir, args.shock, records)


def make_db(output_dir, shock, airlines, records):
    """Create database."""
    db_path = output_dir / f"{shock}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        airlines.write_database("airline", conn, if_table_exists="replace")
        for name, df in records.items():
            if df.is_empty():
                continue
            df.write_database(name, conn, if_table_exists="replace")


def plot_all(output_dir, shock, records):
    """Create and save all plots for a scenario as a single HTML page."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chart = alt.vconcat(
        alt.hconcat(
            plot_delays_over_time(shock, records),
            plot_mishaps_per_day(shock, records),
        ),
        alt.hconcat(
            plot_cumulative_mishaps(shock, records),
            plot_wait_histogram(shock, records),
        ),
        alt.hconcat(
            plot_delay_by_airline(shock, records),
            plot_passenger_flow(shock, records),
        ),
    )
    chart.save(output_dir / f"{shock}.html")


def plot_delays_over_time(shock, records):
    """Total arrival delay per day."""
    flights = (
        records["flight"]
        .with_columns(pl.col("actual_arrival").dt.truncate("1d").alias("day_start"))
        .group_by("day_start")
        .agg(pl.col("arrival_delay_min").sum().alias("total_delay"))
        .sort("day_start")
    )
    return (
        alt.Chart(flights)
        .mark_bar()
        .encode(
            x=alt.X("day_start:T", title="date"),
            y=alt.Y("total_delay:Q", title="total delay (minutes)"),
            tooltip=[
                alt.Tooltip("day_start:T", title="date", format="%Y-%m-%d"),
                alt.Tooltip("total_delay:Q", title="delay (min)", format=".0f"),
            ],
        )
        .properties(title=f"{shock}: total arrival delay per day", width=PLOT_WIDTH)
    )


def plot_mishaps_per_day(shock, records):
    """Number of mishaps per day."""
    mishaps = (
        records["mishap"]
        .with_columns(pl.col("occurred_at").dt.truncate("1d").alias("day_start"))
        .group_by("day_start")
        .agg(pl.len().alias("count"))
        .sort("day_start")
    )
    return (
        alt.Chart(mishaps)
        .mark_bar()
        .encode(
            x=alt.X("day_start:T", title="date"),
            y=alt.Y("count:Q", title="mishaps"),
            tooltip=[
                alt.Tooltip("day_start:T", title="date", format="%Y-%m-%d"),
                alt.Tooltip("count:Q", title="mishaps"),
            ],
        )
        .properties(title=f"{shock}: mishaps per day", width=PLOT_WIDTH)
    )


def plot_cumulative_mishaps(shock, records):
    """Cumulative number of mishaps over time."""
    mishaps = (
        records["mishap"]
        .sort("occurred_at")
        .with_columns(pl.lit(1).cum_sum().alias("cumulative"))
    )
    return (
        alt.Chart(mishaps)
        .mark_line()
        .encode(
            x=alt.X("occurred_at:T", title="time"),
            y=alt.Y("cumulative:Q", title="cumulative mishaps"),
            tooltip=[
                alt.Tooltip("occurred_at:T", title="time", format="%Y-%m-%d %H:%M"),
                alt.Tooltip("cumulative:Q", title="cumulative mishaps"),
            ],
        )
        .properties(title=f"{shock}: cumulative mishaps", width=PLOT_WIDTH)
    )


def plot_wait_histogram(shock, records):
    """Distribution of wait time for rebooked passengers."""
    mishaps = records["mishap"].filter(pl.col("wait_min").is_not_null())
    return (
        alt.Chart(mishaps)
        .mark_bar()
        .encode(
            x=alt.X("wait_min:Q", title="wait (minutes)", bin=True),
            y=alt.Y("count()", title="mishaps"),
            tooltip=[
                alt.Tooltip("wait_min:Q", title="wait (min)", bin=True),
                alt.Tooltip("count()", title="mishaps"),
            ],
        )
        .properties(
            title=f"{shock}: wait time for rebooked passengers", width=PLOT_WIDTH
        )
    )


def plot_delay_by_airline(shock, records):
    """Arrival delay per airline."""
    flights = records["flight"].filter(pl.col("arrival_delay_min").is_not_null())
    return (
        alt.Chart(flights)
        .mark_boxplot()
        .encode(
            x=alt.X("airline_id:N", title="airline"),
            y=alt.Y("arrival_delay_min:Q", title="arrival delay (minutes)"),
            tooltip=[
                alt.Tooltip("airline_id:N", title="airline"),
                alt.Tooltip("arrival_delay_min:Q", title="delay (min)", format=".1f"),
            ],
        )
        .properties(title=f"{shock}: arrival delay by airline", width=PLOT_WIDTH)
    )


def plot_passenger_flow(shock, records):
    """Passenger arrivals and departures per hour."""
    passengers = records["passenger"]
    arrivals = (
        passengers.with_columns(pl.col("arrived_at").dt.truncate("1h").alias("hour"))
        .group_by("hour")
        .agg(pl.len().alias("arrivals"))
    )
    departures = (
        passengers.with_columns(pl.col("departed_at").dt.truncate("1h").alias("hour"))
        .group_by("hour")
        .agg(pl.len().alias("departures"))
    )
    combined = (
        arrivals.join(departures, on="hour", how="full").sort("hour").fill_null(0)
    )
    long = pl.concat(
        [
            combined.select("hour", pl.col("arrivals").alias("count")).with_columns(
                pl.lit("arrivals").alias("flow")
            ),
            combined.select("hour", pl.col("departures").alias("count")).with_columns(
                pl.lit("departures").alias("flow")
            ),
        ]
    )
    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("hour:T", title="time"),
            y=alt.Y("count:Q", title="passengers", stack=True),
            color=alt.Color(
                "flow:N",
                scale=alt.Scale(domain=["arrivals", "departures"]),
                legend=alt.Legend(title="flow"),
            ),
            tooltip=[
                alt.Tooltip("hour:T", title="hour", format="%Y-%m-%d %H:%M"),
                alt.Tooltip("flow:N", title="flow"),
                alt.Tooltip("count:Q", title="passengers"),
            ],
        )
        .properties(title=f"{shock}: passenger flow per hour", width=PLOT_WIDTH)
    )


def post_process(world, airlines):
    """Convert minutes to wall-clock datetimes and add derived columns."""
    flights = pl.from_dicts(
        [
            {
                "flight_id": f.flight_id,
                "airline_id": f.airline_id,
                "origin": f.origin,
                "destination": f.destination,
                "sched_arrival": minutes_to_datetime(f.sched_arrival),
                "actual_arrival": minutes_to_datetime(f.actual_arrival),
                "sched_departure": minutes_to_datetime(f.sched_departure),
                "actual_departure": minutes_to_datetime(f.actual_departure),
                "arrival_delay_min": round(f.actual_arrival - f.sched_arrival, 1),
                "departure_delay_min": (
                    round(f.actual_departure - f.sched_departure, 1)
                    if f.actual_departure is not None
                    else None
                ),
                "capacity": f.capacity,
            }
            for f in Flight._all
        ]
    )

    passengers = pl.from_dicts(
        [
            {
                "passenger_id": p["passenger_id"],
                "family": p["family"],
                "personal": p["personal"],
                "kind": p["kind"],
                "origin": p["origin"],
                "destination": p["destination"],
                "arrival_flight_id": p["arrival_flight_id"],
                "departure_flight_id": p["departure_flight_id"],
                "arrived_at": minutes_to_datetime(p["arrived_at"]),
                "departed_at": minutes_to_datetime(p["departed_at"]),
            }
            for p in world.passengers
        ]
    )

    pax = {p["passenger_id"]: p for p in world.passengers}
    mishaps = (
        pl.from_dicts(
            [
                {
                    "mishap_id": m["mishap_id"],
                    "passenger_id": m["passenger_id"],
                    "missed_flight_id": m["missed_flight_id"],
                    "rebooked_flight_id": m["rebooked_flight_id"],
                    "reason": m["reason"],
                    "occurred_at": minutes_to_datetime(m["occurred_at"]),
                    "wait_min": _wait_minutes(pax[m["passenger_id"]]),
                }
                for m in world.mishaps
            ]
        )
        if world.mishaps
        else pl.DataFrame()
    )

    records = {
        "flight": flights,
        "passenger": passengers,
        "mishap": mishaps,
    }
    return airlines, records


def _wait_minutes(p):
    """Time a rebooked passenger waited, in minutes."""
    if p["arrived_at"] is None or p["departed_at"] is None:
        return None
    return round(p["departed_at"] - p["arrived_at"], 1)


# ----------------------------------------------------------------------


class World:
    """Hold simulation artefacts."""

    def __init__(self, seed, shock):
        self.rng = np.random.default_rng(seed)
        self.shock = shock
        self.fake = Faker(locale=LOCALE)
        self.flight_by_id = {}
        self.inbound = {}
        self.passengers = []
        self.mishaps = []
        self.airline_ids = []
        self.flight_id = id_generator("F", 4)
        self.passenger_id = id_generator("P", 6)
        self.mishap_id = id_generator("M", 6)
        self.delay_probability = DELAY_PROBABILITY
        self.delay_max = DELAY_MAX
        self.struck_airline = None
        self.closure_until = None

    def draw_delay(self, flight, now):
        """Delay in minutes for a flight at the given time."""
        delay = 0.0
        if self.rng.random() < self.delay_probability:
            delay = self.rng.uniform(DELAY_MIN, self.delay_max)
        if self.struck_airline is not None and flight.airline_id == self.struck_airline:
            delay += self.rng.uniform(STRIKE_DELAY_MIN, STRIKE_DELAY_MAX)
        if self.closure_until is not None and now < self.closure_until:
            delay = max(delay, self.closure_until - now)
        return delay

    def deplane(self, flight):
        """Release arriving passengers when a flight lands."""
        now = flight.now
        for p in self.inbound.get(flight.flight_id, []):
            p["arrived_at"] = now
            if p["kind"] == "terminating":
                p["departed_at"] = now
            else:
                outbound = self.flight_by_id[p["departure_flight_id"]]
                if now + MINIMUM_CONNECTION_TIME > outbound.sched_departure:
                    self.rebook(p, outbound, "missed", now)
                else:
                    outbound.manifest.append(p)

    def board(self, flight):
        """Board a departing flight, bumping passengers if it is full."""
        now = flight.now
        manifest = sorted(flight.manifest, key=lambda p: p["arrived_at"])
        for p in manifest[: flight.capacity]:
            p["departed_at"] = now
        for p in manifest[flight.capacity :]:
            self.rebook(p, flight, "bumped", now)

    def rebook(self, passenger, missed_flight, reason, now):
        """Move a passenger onto the next flight to their destination."""
        next_flight = self.next_flight_to(passenger["destination"], missed_flight)
        passenger["departure_flight_id"] = (
            next_flight.flight_id if next_flight is not None else None
        )
        self.mishaps.append(
            {
                "mishap_id": next(self.mishap_id),
                "passenger_id": passenger["passenger_id"],
                "missed_flight_id": missed_flight.flight_id,
                "rebooked_flight_id": next_flight.flight_id if next_flight else None,
                "reason": reason,
                "occurred_at": now,
            }
        )
        if next_flight is not None:
            next_flight.manifest.append(passenger)

    def next_flight_to(self, destination, after_flight):
        """Earliest not-yet-departed flight to a destination after a given flight."""
        candidates = [
            f
            for f in Flight._all
            if f.destination == destination
            and f.actual_departure is None
            and f.sched_departure > after_flight.sched_departure
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda f: f.sched_departure)
        return candidates[0]

    def rush(self, now):
        """Add extra originating passengers to flights not yet departed."""
        for f in Flight._all:
            if f.sched_departure <= now:
                continue
            for _ in range(int(self.rng.integers(RUSH_EXTRA_MIN, RUSH_EXTRA_MAX + 1))):
                p = make_passenger(
                    self,
                    "originating",
                    None,
                    {
                        "flight_id": f.flight_id,
                        "destination": f.destination,
                        "sched_departure": f.sched_departure,
                    },
                )
                self.passengers.append(p)
                f.manifest.append(p)


class Flight(Process):
    """A flight that arrives, turns around, and departs."""

    _all = []

    def init(self, world, details):
        self.world = world
        self.flight_id = details["flight_id"]
        self.airline_id = details["airline_id"]
        self.origin = details["origin"]
        self.destination = details["destination"]
        self.sched_arrival = details["sched_arrival"]
        self.sched_departure = details["sched_departure"]
        self.capacity = details["capacity"]
        self.actual_arrival = None
        self.actual_departure = None
        self.manifest = []
        Flight._all.append(self)
        world.flight_by_id[self.flight_id] = self

    async def run(self):
        await self.timeout(self.sched_arrival)
        arrival_delay = self.world.draw_delay(self, self.now)
        if arrival_delay > 0:
            await self.timeout(arrival_delay)
        self.actual_arrival = self.now
        self.world.deplane(self)

        await self.timeout(self.sched_departure - self.sched_arrival)
        departure_delay = self.world.draw_delay(self, self.now)
        if departure_delay > 0:
            await self.timeout(departure_delay)
        self.actual_departure = self.now
        self.world.board(self)


class Shock(Process):
    """Applies a system-wide shock to the simulation at a scheduled time."""

    def init(self, world):
        self.world = world

    async def run(self):
        await self.timeout(SIMULATION_TIME / 2)
        match self.world.shock:
            case "plain":
                pass

            case "weather":
                self.world.delay_probability = WEATHER_DELAY_PROBABILITY
                self.world.delay_max = WEATHER_DELAY_MAX

            case "strike":
                idx = int(self.world.rng.integers(len(self.world.airline_ids)))
                self.world.struck_airline = self.world.airline_ids[idx]

            case "storm":
                self.world.closure_until = self.now + STORM_DURATION

            case "rush":
                self.world.rush(self.now)

            case _:
                raise ValueError(f"unknown shock {self.world.shock}")


def simulate(world, flights):
    """Create processes and run the simulation."""
    env = Environment()
    for f in flights:
        Flight(env, world, f)

    world.inbound = {}
    for p in world.passengers:
        if p["arrival_flight_id"] is not None:
            world.inbound.setdefault(p["arrival_flight_id"], []).append(p)
        else:
            world.flight_by_id[p["departure_flight_id"]].manifest.append(p)

    Shock(env, world)
    env.run(until=SIMULATION_TIME + RUN_OVERRUN)


# ----------------------------------------------------------------------


def minutes_to_datetime(t):
    """Convert simulation minutes to wall-clock datetime, truncated to minute."""
    if t is None:
        return None
    return (SIMULATION_START + timedelta(minutes=t)).replace(second=0, microsecond=0)


def id_generator(stem, digits):
    """Generate unique IDs of the form 'stemDDDD'."""

    i = 1
    while True:
        temp = str(i)
        assert len(temp) <= digits, f"ID generation overflow {stem}: {i}"
        yield f"{stem}{temp.zfill(digits)}"
        i += 1


def make_airlines(world):
    """Create the airlines."""
    world.airline_ids = [code for code, _ in AIRLINES]
    return pl.from_dicts(
        [{"airline_id": code, "name": name} for code, name in AIRLINES]
    )


def make_flights(world):
    """Create the flight schedule."""
    flights = []
    for airline_id in world.airline_ids:
        for _ in range(FLIGHTS_PER_AIRLINE_PER_DAY * NUM_DAYS):
            sched_arrival = world.rng.uniform(0, SIMULATION_TIME - TURNAROUND_MAX)
            turnaround = world.rng.uniform(TURNAROUND_MIN, TURNAROUND_MAX)
            origin = CITIES[int(world.rng.integers(len(CITIES)))]
            destination = CITIES[int(world.rng.integers(len(CITIES)))]
            while destination == origin:
                destination = CITIES[int(world.rng.integers(len(CITIES)))]
            flights.append(
                {
                    "flight_id": next(world.flight_id),
                    "airline_id": airline_id,
                    "origin": origin,
                    "destination": destination,
                    "sched_arrival": sched_arrival,
                    "sched_departure": sched_arrival + turnaround,
                    "capacity": int(world.rng.integers(SEATS_MIN, SEATS_MAX + 1)),
                }
            )
    return flights


def make_passengers(world, flights):
    """Create passengers for every flight."""
    passengers = []
    for f in flights:
        for _ in range(int(world.rng.integers(ORIGINATING_MIN, ORIGINATING_MAX + 1))):
            passengers.append(make_passenger(world, "originating", None, f))

        for _ in range(int(world.rng.integers(TERMINATING_MIN, TERMINATING_MAX + 1))):
            passengers.append(make_passenger(world, "terminating", f, None))

        candidates = [
            d
            for d in flights
            if d["sched_departure"] > f["sched_arrival"] + MINIMUM_CONNECTION_TIME
            and d["sched_departure"]
            <= f["sched_arrival"] + MINIMUM_CONNECTION_TIME + CONNECTION_WINDOW
            and d["destination"] != f["origin"]
        ]
        for _ in range(int(world.rng.integers(CONNECTING_MIN, CONNECTING_MAX + 1))):
            if not candidates:
                break
            d = candidates[int(world.rng.integers(len(candidates)))]
            passengers.append(make_passenger(world, "connecting", f, d))

    return passengers


def make_passenger(world, kind, arr_flight, dep_flight):
    """Create a single passenger."""
    if kind == "originating":
        origin, destination = HUB_CITY, dep_flight["destination"]
        arrival_flight_id, departure_flight_id = None, dep_flight["flight_id"]
        arrived_at = dep_flight["sched_departure"] - world.rng.uniform(
            CHECKIN_MIN, CHECKIN_MAX
        )
    elif kind == "terminating":
        origin, destination = arr_flight["origin"], HUB_CITY
        arrival_flight_id, departure_flight_id = arr_flight["flight_id"], None
        arrived_at = None
    else:
        origin, destination = arr_flight["origin"], dep_flight["destination"]
        arrival_flight_id, departure_flight_id = (
            arr_flight["flight_id"],
            dep_flight["flight_id"],
        )
        arrived_at = None

    return {
        "passenger_id": next(world.passenger_id),
        "family": world.fake.last_name(),
        "personal": world.fake.first_name(),
        "kind": kind,
        "origin": origin,
        "destination": destination,
        "arrival_flight_id": arrival_flight_id,
        "departure_flight_id": departure_flight_id,
        "arrived_at": arrived_at,
        "departed_at": None,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Synthesize airport data via DES")
    parser.add_argument("--out", type=str, default=".", help="output directory")
    parser.add_argument("--seed", type=int, default=SEED, help="RNG seed")
    parser.add_argument(
        "--shock",
        default="plain",
        choices=["plain", "weather", "strike", "rush", "storm"],
        help="shocks to the system",
    )
    return parser.parse_args()


# ----------------------------------------------------------------------


if __name__ == "__main__":
    main()
