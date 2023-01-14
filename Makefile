.DEFAULT_GOAL := help
PROJECT_NAME:=$(shell poetry version | sed -e "s/ .*//g")
ALL_PYTHON_FILES:=$(shell find ./src -name "*.py" 2> /dev/null && find ./tests -name "*.py" 2> /dev/null)

AWS_ACCOUNT_ID=$(shell aws sts get-caller-identity --query "Account" --output text)
AWS_REGION=$(shell aws configure get region)
AWS_ACCESS_KEY_ID=$(shell aws configure get aws_access_key_id)
AWS_ACCESS_SECRET_KEY=$(shell aws configure get aws secret_access_key)
AWS_CURRENT_ECS_TASKS=$(shell aws ecs list-tasks --cluster crypto-trading-cluster --query "taskArns" --output text)

AWS_ECS_CLUSTER:=crypto-trading-cluster
AWS_FARGATE:=crypto-trading-service
AWS_ECR:=crypto_trading_ecr


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

deploy: publish stop_tasks
	aws ecs update-service --cluster $(AWS_ECS_CLUSTER) --service $(AWS_FARGATE) --force-new-deployment > /dev/null || true

make parallel_backtest:
	make backtest args='{"n_candles": 5, "high_factor": 0.5, "retracement_factor": 0.5, "max_abs_slope": 0.005, "trend_candles": 3, "sideways_factor": 2}' & \
	make backtest args='{"n_candles": 10, "high_factor": 0.5, "retracement_factor": 0.5, "max_abs_slope": 0.005, "trend_candles": 3, "sideways_factor": 2}' & \
	make backtest args='{"n_candles": 15, "high_factor": 0.5, "retracement_factor": 0.5, "max_abs_slope": 0.005, "trend_candles": 3, "sideways_factor": 2}'