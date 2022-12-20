SHELL := bash
.DEFAULT_GOAL := help
PROJECT_NAME:=$(shell poetry version | sed -e "s/ .*//g")
ALL_PYTHON_FILES:=$(shell find ./src -name "*.py" 2> /dev/null && find ./tests -name "*.py" 2> /dev/null)

check:
	poetry check

install: check
	poetry install --no-root $(no_dev)
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

backtest:
	poetry run python -m src.backtest.run_backtest --ticker 'BTCUSDT' --freqs '1 5 15' --model_args '$(args)' --start_history '2021-12-31' --start_str '2022-01-01' --end_str '2022-04-01'

main:
	make install no_dev=--no-dev
	poetry run python -m main
	
# add arguments via --build-arg VARIABLE=value
docker:
	docker build .
run: docker
	docker run

make parallel_backtest:
	make backtest args='{"n_candles": 5, "high_factor": 0.5, "retracement_factor": 0.5, "max_abs_slope": 0.005, "trend_candles": 3, "sideways_factor": 2}' & \
	make backtest args='{"n_candles": 10, "high_factor": 0.5, "retracement_factor": 0.5, "max_abs_slope": 0.005, "trend_candles": 3, "sideways_factor": 2}' & \
	make backtest args='{"n_candles": 15, "high_factor": 0.5, "retracement_factor": 0.5, "max_abs_slope": 0.005, "trend_candles": 3, "sideways_factor": 2}'