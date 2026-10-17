# Claude

This Python project contains simple simulators used to generate data for use in
teaching data science in Python.  The simulators use the `asimpy` package for
discrete event simulation and `altair`

## Call Center

`calls.py` simulates a call center. The basic scenario models clients and agents
whose behavior does not change over time. Three other scenarios model changes in
behavior.

## Structure

-   Each simulation is in a single Python file.
    -   `calls.py`: simulate a call center.
    -   `airport.py`: simulate an airport.
-   Other files:
    -   `README.md`: project home page (do not modify).
    -   `LICENSE.md`: license (do not modify).
    -   `CODE_OF_CONDUCT.md`: code of conduct (do not modify).
-   This project has a `uv` virtual environment, so use `uv run` rather than
    `python3` to run commands.

## Build and Test Commands

-   Repeatable actions are saved in `Makefile`.
-   Use `python calls.py` to run the call center simulation.
-   Use `python airport.py` to run the airport simulation.

## Style Rules

-   Do not use type annotations.
-   Keep docstrings short and do not bother to document parameters.
-   Use named constants declared at the top of the file rather than magic
    numbers.
-   Put all imports at the top of the file.
-   Use minutes for all calculations.
-   Store datetime objects in the SQLite database. If durations must be stored,
    store them in minutes.
