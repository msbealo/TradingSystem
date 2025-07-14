import sqlite3
import pandas as pd
import backtrader as bt
import yfinance as yf
from datetime import datetime

# Database connection
DB_FILE = "trading_system.db"

def get_portfolio_stocks(portfolio_id):
    """Retrieve all stock tickers associated with a portfolio."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT stock_ticker FROM portfolio_stocks WHERE portfolio_id = ?", (portfolio_id,))
    stocks = [row[0] for row in cursor.fetchall()]
    conn.close()
    return stocks

def get_historical_prices(stock_ticker, start_date="2020-01-01"):
    """Retrieve historical stock prices from the database or fetch from Yahoo Finance if missing."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, open_price, high_price, low_price, close_price, adjusted_close, volume
        FROM historical_prices WHERE ticker = ? ORDER BY date ASC
    """, (stock_ticker,))
    
    rows = cursor.fetchall()
    conn.close()

    if rows:
        df = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "adj_close", "volume"])
    else:
        # Fetch from Yahoo Finance if missing
        df = yf.download(stock_ticker, start=start_date, progress=False)
        df.reset_index(inplace=True)
        df.rename(columns={"Date": "datetime", "Open": "open", "High": "high", "Low": "low", 
                           "Close": "close", "Adj Close": "adj_close", "Volume": "volume"}, inplace=True)

    # Ensure datetime column is correctly formatted
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    # Select only required columns for Backtrader
    df = df[["open", "high", "low", "close", "volume"]]

    # Ensure all column names are lowercase
    df.columns = df.columns.str.lower()

    return df


class AITradingStrategy(bt.Strategy):
    params = (("strategy_json", None),)  # Define parameters correctly

    def __init__(self):
        self.indicators = {}
        self.strategy_json = self.params.strategy_json  # Ensure strategy JSON is stored correctly

        if not self.strategy_json:
            raise ValueError("No strategy JSON provided to AITradingStrategy.")

        # Set up indicators dynamically
        for indicator in self.strategy_json["indicators"]:
            ind_type = indicator["type"]
            params = indicator["parameters"]

            if ind_type == "RSI":
                self.indicators[ind_type] = bt.indicators.RSI(period=params["period"])
            elif ind_type == "MACD":
                self.indicators[ind_type] = bt.indicators.MACD(
                    fast=params["fast"], slow=params["slow"], signal=params["signal"]
                )

    def next(self):
        entry_conditions_met = all(
            (self.indicators[ind["type"]] < ind["value"] if ind["condition"] == "<" else
             self.indicators[ind["type"]] > ind["value"])
            for ind in self.strategy_json["indicators"]
        )

        exit_condition = self.strategy_json["exit_condition"]
        exit_met = (self.indicators[exit_condition["type"]] > exit_condition["value"] 
                    if exit_condition["condition"] == ">" else 
                    self.indicators[exit_condition["type"]] < exit_condition["value"])

        if entry_conditions_met:
            self.buy()
        elif exit_met:
            self.sell()

def run_backtest(portfolio_id, strategy_json, start_date="2020-01-01"):
    """Run a backtest for all stocks in a portfolio using AI-generated strategy."""
    cerebro = bt.Cerebro()
    
    # Ensure strategy JSON is correctly passed
    cerebro.addstrategy(AITradingStrategy, strategy_json=strategy_json)

    stocks = get_portfolio_stocks(portfolio_id)
    added_data = False  # Track if we add at least one stock to Backtrader

    for stock in stocks:
        df = get_historical_prices(stock, start_date)

        if df.empty:
            print(f"Warning: No data found for {stock}. Skipping.")
            continue

        # Ensure datetime is the index and columns are correct
        print(f"Loading {stock} into Backtrader with columns: {df.columns}")

        try:
            data = bt.feeds.PandasData(dataname=df)
            cerebro.adddata(data)
            added_data = True
        except Exception as e:
            print(f"Error adding {stock}: {e}")

    if not added_data:
        print("Error: No valid stock data available for backtesting.")
        return

    cerebro.run()
    cerebro.plot()

