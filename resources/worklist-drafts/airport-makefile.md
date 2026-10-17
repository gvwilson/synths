# Before

`Makefile` has `calls` and `calls-*` targets running `python calls.py [--shock ...]`,
plus `check`, `fix`, `format`, `clean`, and `commands`. No airport targets exist.

# After

Add `airport` targets mirroring the `calls` targets:

- `airport` — runs `airport-plain airport-weather airport-strike airport-rush airport-storm`
- `airport-plain` — `python airport.py`
- `airport-weather` — `python airport.py --shock weather`
- `airport-strike` — `python airport.py --shock strike`
- `airport-rush` — `python airport.py --shock rush`
- `airport-storm` — `python airport.py --shock storm`
