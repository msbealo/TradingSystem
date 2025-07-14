from database import TradingDatabase
from data_fetcher import StockDataFetcher
from backtest_engine import BacktsestEngine
from chatgpt_api import ChatGPTAPI
from Strategy_builder import build_strategy_class
import datetime
import os

# 1️⃣ Initialize Components
db = TradingDatabase()
fetcher = StockDataFetcher(db)
backtest_engine = BacktsestEngine(db)
chat_api = ChatGPTAPI()

# 2️⃣ Create Portfolio
portfolio_name = "Test Portfolio"
capital = 100000
execution_mode = "paper"

db.add_portfolio(name=portfolio_name, capital=capital, execution_mode=execution_mode)
portfolios = db.get_portfolios()
portfolio_id = portfolios[-1][0]  # Get the last added portfolio

# 3️⃣ Download Price Data and Add Stocks to Portfolio
# tickers = ["AAPL", "MSFT", "GOOGL"]
tickers = ["AAPL"]
for ticker in tickers:
    fetcher.sync_stock_info(ticker)
    fetcher.fetch_price_data(ticker, start_date="2020-01-01")
    db.add_stock(portfolio_id, ticker)

strategy_requests = [
    # Moving Averages
    "Create a strategy using SMA where it buys when the 20-day SMA crosses above the 50-day SMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",
    "Create a strategy using EMA where it buys when the 10-day EMA crosses above the 30-day EMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",
    "Create a strategy using WMA where it buys when the 15-day WMA crosses above the 30-day WMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",
    "Create a strategy using DEMA where it buys when the 10-day DEMA crosses above the 20-day DEMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",
    "Create a strategy using TEMA where it buys when the 10-day TEMA crosses above the 20-day TEMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",
    "Create a strategy using SMMA where it buys when the 10-day SMMA crosses above the 30-day SMMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",  # changed from > to crossover
    "Create a strategy using HMA with a period of 50 where it buys when price crosses above the HMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",  # changed to crossover
    "Create a strategy using ZLEMA where it buys when the 10-day ZLEMA crosses above the 30-day ZLEMA and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",

    # Momentum / Oscillators
    "Create a trading strategy using RSI where it buys when RSI is below 40 and sells when it rises above 60. Use a take_profit of 100 and position_size of 1.0",
    "Create a trading strategy using MACD where it buys when MACD crosses above the signal line and sells when it crosses below. Use a take_profit of 100 and position_size of 1.0",
    "Create a trading strategy using STOCH where it buys when %K crosses above %D and sells when %K crosses below %D. Use a take_profit of 100 and position_size of 1.0",  # simplified, removed 20/80 to increase triggers
    "Create a strategy using MOMENTUM where it buys when the momentum value is greater than 0 and sells when it turns negative. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using ROC where it buys when ROC rises above zero and sells when it drops below zero. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using TRIX where it buys when TRIX crosses above zero and sells when it crosses below. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using CCI where it buys when CCI is below -100 and sells when it goes above 100. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using UO where it buys when the Ultimate Oscillator is below 40 and sells when it rises above 60. Use a take_profit of 100 and position_size of 1.0",  # relaxed from 30/70
    "Create a strategy using AO where it buys when the Awesome Oscillator crosses above zero and sells when it crosses below. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using PPO where it buys when PPO crosses above its signal line and sells when it crosses below. Use a take_profit of 100 and position_size of 1.0",

    # Volatility / Range
    "Create a strategy using ATR where it buys when ATR is rising and momentum is positive, and sells when momentum turns negative. Use a take_profit of 100 and position_size of 1.0",  # removed 'recent high/low' for simplicity
    "Create a strategy using BOLLINGER where it buys when the price is below the lower Bollinger Band and sells when it rises above the upper band. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using BBANDS where it buys when the close is below the lower BBand and sells when it rises above the upper BBand. Use a take_profit of 100 and position_size of 1.0",

    # Trend / Direction
    "Create a strategy using ADX where it buys when ADX is above 25 and +DI crosses above -DI, and sells when -DI crosses above +DI. Use a take_profit of 100 and position_size of 1.0",  # converted DI comparisons to crosses
    "Create a strategy using ADXR where it buys when ADXR is above 20 and +DI crosses above -DI, and sells when it crosses below. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using PLUS_DI where it buys when PLUS_DI crosses above MINUS_DI and sells when it crosses below. Use a take_profit of 100 and position_size of 1.0",  # simplified from dual-condition
    "Create a strategy using MINUS_DI where it buys when MINUS_DI crosses below PLUS_DI and sells when it crosses above. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using SAR where it buys when price crosses above the Parabolic SAR and sells when it crosses below. Use a take_profit of 100 and position_size of 0.9",

    # Other
    "Create a strategy using AROONUPDOWN where it buys when Aroon Up crosses above Aroon Down and sells when Aroon Down crosses above Aroon Up. Use a take_profit of 100 and position_size of 1.0",  # replaced dual value-based conditions
    "Create a strategy using AROONOSC where it buys when the Aroon Oscillator crosses above zero and sells when it crosses below. Use a take_profit of 100 and position_size of 1.0",
    "Create a strategy using HEIKINASHI where it buys when the Heikin Ashi close is greater than the current price and sells when it is lower. Use a take_profit of 100 and position_size of 1.0",  # gives the model a way to output valid condition
    "Create a strategy using ICHIMOKU where it buys when price crosses above Senkou A and sells when it crosses below Senkou B. Use a take_profit of 100 and position_size of 1.0"
]

strategies = []
for request in strategy_requests:
    strategy_json = chat_api.generate_trading_strategy(user_input=request)
    if "error" not in strategy_json:
        strategy_name = strategy_json['strategy_name']
        db.add_strategy(strategy_name, strategy_json, [portfolio_id])

# 5️⃣ Prepare Strategies for Backtesting
db_strategies = db.get_strategies(portfolio_id)
for strat in db_strategies:
    strategy_class = build_strategy_class(strat['parameters'])
    assigned_stocks = [s[2] for s in db.get_stocks(portfolio_id)]
    strategies.append({
        "name": strat['name'],
        "class": strategy_class,
        "stocks": assigned_stocks
    })

# 6️⃣ Prepare Portfolio Dictionary
portfolio = {"capital": capital}

# 7️⃣ Run the Backtest
results = backtest_engine.run_portfolio_backtest(
    portfolio,
    strategies,
    start_date="2020-01-01",
    end_date=datetime.datetime.now().strftime('%Y-%m-%d')
)

# 8️⃣ Print Results
print("\n=== Backtest Portfolio Results ===")
print(f"Cumulative Return: {results['cumulative_return']:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
print(f"Win Rate: {results['win_rate']:.2f}%")
print(f"Total Trades: {results['total_trades']}")
print(f"Winning Trades: {results['winning_trades']}")
print(f"Losing Trades: {results['losing_trades']}")

# 9️⃣ Save extended daily log CSV files for each (strategy, stock) combination
detailed_results = results.get("detailed_results", [])
for detail in detailed_results:
    strategy_name = detail["strategy"]
    stock = detail["stock"]
    daily_log_df = detail.get("indicator_log_df")
    if daily_log_df is not None and not daily_log_df.empty:
        # Create a filename that combines strategy name and stock ticker (sanitize as needed)
        folder_path = "Strategy_Trade_History"
        os.makedirs(folder_path, exist_ok=True)
        filename = os.path.join(folder_path, f"{strategy_name.replace(' ', '_')}_{stock}_daily_log.csv")
        daily_log_df.to_csv(filename, index=False)
        print(f"Saved daily log CSV: {filename}")
    else:
        print(f"No daily log available for {strategy_name} on {stock}.")