.DEFAULT_GOAL := help
PROJECT_NAME:=$(shell poetry version | sed -e "s/ .*//g")
ALL_PYTHON_FILES:=$(shell find ./src -name "*.py" 2> /dev/null && find ./tests -name "*.py" 2> /dev/null)

check:
	poetry check

install:
	poetry install
lock:
	poetry lock

lint:
	poetry run yapf -i -r --style google -vv -e .venv -e ._env .

autolint: lint
	poetry run isort ${ALL_PYTHON_FILES}

type-check:
	poetry run mypy src --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs

clean:
	rm -f -r ./build/
	rm -f -r ./dist/
	rm -f -r *.egg-info
	rm -f .coverage

unittest: clean lint
	poetry run coverage run --source src -m unittest discover -v -s ./tests -p test*.py
	poetry run coverage report -m --fail-under 0
	poetry run coverage html -d build/unittest-coverage
	poetry run coverage html -d build/unittest-coverage.json --pretty-print
	poetry run coverage erase