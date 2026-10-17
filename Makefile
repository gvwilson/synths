.PHONY: docs
all: commands

CALLS_SCRIPT=calls.py --out calls
AIRPORT_SCRIPT=airport.py --out airport

## calls: create all scenarios
calls: calls-plain calls-followup calls-newclients calls-overload calls-special

## calls-plain: create with no shocks to the system
calls-plain:
	@python ${CALLS_SCRIPT}

## calls-followup: create with increase in followup time
calls-followup:
	@python ${CALLS_SCRIPT} --shock followup

## calls-overload: agents have too much work
calls-overload:
	@python ${CALLS_SCRIPT} --shock overload

## calls-newclients: create with new clients
calls-newclients:
	@python ${CALLS_SCRIPT} --shock newclients

## calls-special: create with special offer
calls-special:
	@python ${CALLS_SCRIPT} --shock special

## ---: ---

## airport: create all airport scenarios
airport: airport-plain airport-weather airport-strike airport-rush airport-storm

## airport-plain: create with no shocks to the system
airport-plain:
	@python ${AIRPORT_SCRIPT}

## airport-weather: create with widespread delays
airport-weather:
	@python ${AIRPORT_SCRIPT} --shock weather

## airport-strike: one airline's flights are heavily delayed
airport-strike:
	@python ${AIRPORT_SCRIPT} --shock strike

## airport-rush: extra passengers overwhelm flights
airport-rush:
	@python ${AIRPORT_SCRIPT} --shock rush

## airport-storm: airport closed for a window
airport-storm:
	@python ${AIRPORT_SCRIPT} --shock storm

## ---: ---

## commands: show available commands (*)
commands:
	@grep -h -E '^##' ${MAKEFILE_LIST} \
	| sed -e 's/## //g' \
	| column -t -s ':'

## check: check code issues
check:
	@ruff check .

## clean: clean up
clean:
	@rm -rf ./dist ./tmp
	@find . -path './.venv' -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	@find . -path './.venv' -prune -o -type f -name '*~' -exec rm {} +
	@rm -f *.db *.html calls airport

## fix: fix code issues
fix:
	ruff check --fix .

## format: format code
format:
	ruff format .
