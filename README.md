# Crypto Trading Bot

The Crypto Trading Bot project is a Python-based trading bot designed to interact with the Bybit API for cryptocurrency trading. The bot is configured using a dedicated configuration file located in the `config` folder. All sensitive credentials, such as API keys, are expected to be stored securely in a `.env` file. An example template for the `.env` file can be found in `example.env`.

PLEASE BE AWARE THAT THIS IS STILL IN DEVELOPMENT AND BUGS MAY POP UP AT TIMES. SO NOT USE IN PRODUCTION BEFORE PROPER TESTING.

## Project Structure

- **config**: Folder containing the configuration file for the trading bot.
- **src**: Source code for the trading bot.
- **tests**: Unit tests for the trading bot.
- **.env**: File to store sensitive credentials for API authentication.
- **example.env**: Example template for the `.env` file.

## Dependency Management

The project manages dependencies using [Poetry](https://python-poetry.org/), a modern Python dependency management tool. Before running any make commands, ensure that Poetry is installed on your system. You can install Poetry by following the instructions [here](https://python-poetry.org/docs/#installation).

Additionally, the project utilizes [Make](https://www.gnu.org/software/make/) as a build automation tool. If you don't have Make installed, you can install it on Unix-like systems using a package manager like [Homebrew](https://brew.sh/) (for macOS) or [apt](https://linux.die.net/man/8/apt) (for Debian/Ubuntu Linux).

## Setup
You need a babyit account with api endpoints to use the bot. You can set up the account with endpoints for free on bybit.com. Then add your credentials in the template `example.env` and rename it to `.env`.
SHARE YOUR CREDENTIALS WITH NOBODY.

## Main Functionalities

### 0. Write your trading strategy
The bot allows the trader to write his entire strategy into a single python script in `src/model/checklist_model.py`. Here the function `checklist_model` serves as the function that is executed by the backend whenever new data arrives via the bybit endpoints. To get you started, an example strategy is implemented that goes long everytime the close price exceeds the open price and goes short whenever the close price is below the open price.

### 1. Run Live Trading Bot

Use the following command to execute the live trading bot:

```bash
make main
```

This command installs the required dependencies, initializes the bot, and starts live trading based on the configurations provided in the `config` folder.

### 2. Run Backtest

Execute the following command to run a backtest using historical Bybit data:

```bash
make backtest
```

The backtest functionality allows you to simulate the trading bot's behavior using historical data. Adjust the parameters for tickers, frequencies, and date ranges in the configuration file as needed.

## AWS Deployment

The project supports deployment on AWS via ECR and Fargate.

### Deployment Commands

- **make ecr**: Creates the AWS ECR repository.
- **make login**: Logs into AWS ECR.
- **make docker**: Builds the Docker image that runs the bot.
- **make publish**: Runs the `make ecr`, `make login`, and `make docker` commands as a pipeline.
- **make stop-tasks**: Stops all ECS tasks.
- **make deploy**: Runs the entire deployment pipeline.

Before using these commands, ensure that AWS credentials are configured locally.

## Getting Started

1. Clone the repository:

   ```bash
   git clone <repository_url>
   ```

2. Navigate to the project directory:

   ```bash
   cd crypto-trading-bot
   ```

3. Create a virtual environment and install dependencies:

   ```bash
   make install
   ```

4. Configure the `.env` file with your Bybit API credentials. Use `example.env` as a template.

5. Run the live trading bot or backtest based on your requirements:

   ```bash
   make main  # For live trading
   ```

   or

   ```bash
   make backtest  # For backtesting
   ```

Ensure that Docker, Poetry, and the AWS CLI are properly installed and configured for certain commands to work as expected. Customize the configuration file and adjust command parameters according to your trading preferences.
```

Feel free to copy the entire content above and use it as your README.md file.