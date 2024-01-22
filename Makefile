.DEFAULT_GOAL := help
PROJECT_NAME:=$(shell poetry version | sed -e "s/ .*//g")
ALL_PYTHON_FILES:=$(shell find ./src -name "*.py" 2> /dev/null && find ./tests -name "*.py" 2> /dev/null)

AWS_ACCOUNT_ID=$(shell aws sts get-caller-identity --query "Account" --output text)
AWS_REGION=$(shell aws configure get region)
AWS_ACCESS_KEY_ID=$(shell aws configure get aws_access_key_id)
AWS_ACCESS_SECRET_KEY=$(shell aws configure get aws_secret_access_key)
AWS_CURRENT_ECS_TASKS_BTC=$(shell aws ecs list-tasks --cluster crypto-trading-cluster --service crypto-trading-service-btc --query "taskArns" --output text)
AWS_CURRENT_ECS_TASKS_ETH=$(shell aws ecs list-tasks --cluster crypto-trading-cluster --service crypto-trading-service-eth --query "taskArns" --output text)
AWS_CURRENT_ECS_TASKS_FUTURES=$(shell aws ecs list-tasks --cluster crypto-trading-cluster --service futures-trading-service --query "taskArns" --output text)

AWS_ECS_CLUSTER:=crypto-trading-cluster

AWS_FARGATE:=crypto-trading-service-btc
AWS_ECR:=crypto_trading_ecr_btc
TICKERS:=BTCUSDT

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
	poetry run python -m src.backtest.run_backtest --tickers '$(TICKERS)' --freqs '1 5' --start_history '2024-01-01 00:00:00' --start_str '2024-01-02 00:00:00' --end_str '2024-01-03 00:00:00'

main:
	make install no_dev='--only main'
	poetry run python -u -m main --tickers '$(TICKERS)' --tick_sizes '$(TICK_SIZES)' --freqs '1 5' --trading_freqs '$(TRADING_FREQS)'
	
# add arguments via --build-arg VARIABLE=value
docker:
	docker build . --build-arg SECRET_KEY=$(AWS_ACCESS_SECRET_KEY) --build-arg ACCESS_KEY=$(AWS_ACCESS_KEY_ID) --build-arg REGION=$(AWS_REGION) --build-arg BUILD_NUMBER=$(version) -t $(AWS_ECR)

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
	for task in $(AWS_CURRENT_ECS_TASKS_FUTURES); do \
		aws ecs stop-task --cluster $(AWS_ECS_CLUSTER) --task $$task > /dev/null || true ; \
	done

deploy: publish stop_tasks
	aws ecs update-service --cluster $(AWS_ECS_CLUSTER) --service $(AWS_FARGATE) --force-new-deployment > /dev/null || true
