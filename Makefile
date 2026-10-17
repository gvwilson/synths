.PHONY: docs
all: commands

SCRIPT=calls.py

## calls: create all scenarios
calls: calls-plain calls-followup calls-newclients calls-overload calls-special

## calls-plain: create with no shocks to the system
calls-plain:
	@python ${SCRIPT}

## calls-followup: create with increase in followup time
calls-followup:
	@python ${SCRIPT} --shock followup

## calls-overload: agents have too much work
calls-overload:
	@python ${SCRIPT} --shock overload

## calls-newclients: create with new clients
calls-newclients:
	@python ${SCRIPT} --shock newclients

## calls-special: create with special offer
calls-special:
	@python ${SCRIPT} --shock special

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
	@rm -f *.db *.html

## fix: fix code issues
fix:
	ruff check --fix .

## format: format code
format:
	ruff format .
