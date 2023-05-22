.DEFAULT_GOAL := help
PROJECT_NAME:=$(shell poetry version | sed -e "s/ .*//g")
ALL_PYTHON_FILES:=$(shell find ./src -name "*.py" 2> /dev/null && find ./tests -name "*.py" 2> /dev/null)

AWS_ACCOUNT_ID=$(shell aws sts get-caller-identity --query "Account" --output text)
AWS_REGION=$(shell aws configure get region)
AWS_ACCESS_KEY_ID=$(shell aws configure get aws_access_key_id)
AWS_ACCESS_SECRET_KEY=$(shell aws configure get aws secret_access_key)
AWS_CURRENT_ECS_TASKS_BTC=$(shell aws ecs list-tasks --cluster crypto-trading-cluster --service crypto-trading-service-btc --query "taskArns" --output text)
AWS_CURRENT_ECS_TASKS_ETH=$(shell aws ecs list-tasks --cluster crypto-trading-cluster --service crypto-trading-service-eth --query "taskArns" --output text)

# AWS_ECS_CLUSTER:=crypto-trading-cluster

# AWS_FARGATE:=crypto-trading-service-btc
# AWS_ECR:=crypto_trading_ecr_btc
# TICKERS:=BTCUSDT

# AWS_FARGATE:=crypto-trading-service-eth
# AWS_ECR:=crypto_trading_ecr_eth
# TICKERS:=ETHUSDT

TICKERS:=RTYUSD
TRADING_FREQS:=1 5
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
	poetry run python -m src.backtest.run_backtest --tickers '$(TICKERS)' --freqs '1 5 15' --trading_freqs '$(TRADING_FREQS)' --model_args '$(args)' --start_history '2022-09-29' --start_str '2022-10-01' --end_str '2023-01-01'

evaluate_backtest_2022:
	poetry run python -m src.backtest.run_backtest --tickers '$(TICKERS)' --freqs '1 5 15' --trading_freqs '$(TRADING_FREQS)' --model_args '$(args)' --start_history '2021-12-29' --start_str '2022-01-01' --end_str '2023-01-01'

evaluate_backtest_2021:
	poetry run python -m src.backtest.run_backtest --tickers '$(TICKERS)' --freqs '1 5 15' --trading_freqs '$(TRADING_FREQS)' --model_args '$(args)' --start_history '2020-12-29' --start_str '2021-01-01' --end_str '2022-01-01'

evaluate_backtest_2020:
	poetry run python -m src.backtest.run_backtest --tickers '$(TICKERS)' --freqs '1 5 15' --trading_freqs '$(TRADING_FREQS)' --model_args '$(args)' --start_history '2019-12-29' --start_str '2020-01-01' --end_str '2021-01-01'

evaluate_backtest_2019:
	poetry run python -m src.backtest.run_backtest --tickers '$(TICKERS)' --freqs '1 5 15' --trading_freqs '$(TRADING_FREQS)' --model_args '$(args)' --start_history '2018-12-29' --start_str '2019-01-01' --end_str '2020-01-01'

evaluate_backtest_2018:
	poetry run python -m src.backtest.run_backtest --tickers '$(TICKERS)' --freqs '1 5 15' --trading_freqs '$(TRADING_FREQS)' --model_args '$(args)' --start_history '2018-01-02' --start_str '2018-01-03' --end_str '2019-01-01'

main:
	make install no_dev=--no-dev
	poetry run python -m main --tickers '$(TICKERS)' --freqs '1 5 15' --trading_freqs '$(TRADING_FREQS)'
	
# add arguments via --build-arg VARIABLE=value
docker:
	docker build . --build-arg BUILD_NUMBER=$(version) -t $(AWS_ECR)

publish: ecr login docker
	docker tag $(AWS_ECR):latest $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR):latest
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(AWS_ECR):latest
	docker logout

ecr:
	aws ecr create-repository --repository-name $(AWS_ECR) > /dev/null || true

login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

run: docker
	docker run $(AWS_ECR):latest

stop_tasks:
	for task in $(AWS_CURRENT_ECS_TASKS); do \
		aws ecs stop-task --cluster $(AWS_ECS_CLUSTER) --task $$task > /dev/null || true ; \
	done

	@if [ $(TICKER) = BTCUSDT ]; then\
		for task in $(AWS_CURRENT_ECS_TASKS_BTC); do \
			aws ecs stop-task --cluster $(AWS_ECS_CLUSTER) --task $$task > /dev/null || true ; \
		done; \
	else \
		for task in $(AWS_CURRENT_ECS_TASKS_ETH); do \
			aws ecs stop-task --cluster $(AWS_ECS_CLUSTER) --task $$task > /dev/null || true ; \
		done; \
	fi

deploy: publish stop_tasks
	aws ecs update-service --cluster $(AWS_ECS_CLUSTER) --service $(AWS_FARGATE) --force-new-deployment > /dev/null || true

make parallel_backtests:
	for param in $(params) ; do \
    	make backtest args='{"param":'$$param'}'; \
	done

make parallel_evaluate_backtests_2018:
	for param in $(params) ; do \
    	make evaluate_backtest_2018 args='{"param":'$$param'}'; \
	done

make parallel_evaluate_backtests_2019:
	for param in $(params) ; do \
    	make evaluate_backtest_2019 args='{"param":'$$param'}'; \
	done

make parallel_evaluate_backtests_2020:
	for param in $(params) ; do \
    	make evaluate_backtest_2020 args='{"param":'$$param'}'; \
	done

make parallel_evaluate_backtests_2021:
	for param in $(params) ; do \
    	make evaluate_backtest_2021 args='{"param":'$$param'}'; \
	done

make parallel_evaluate_backtests_2022:
	for param in $(params) ; do \
    	make evaluate_backtest_2022 args='{"param":'$$param'}'; \
	done