import json
import datetime
from database import TradingDatabase
from chatgpt_api import generate_trading_strategy

# Initialize Database
db = TradingDatabase()

# ====== Check & Create Portfolios ======
print("📌 Setting Up Portfolios...")

existing_portfolios = {p[1]: p[0] for p in db.get_portfolios()}  # Dictionary: {name: id}

portfolios_to_create = [
    ("Dollar Cost Averaging Portfolio", 10000.0, "paper"),
    ("Growth Portfolio", 15000.0, "paper"),
    ("Value Investing Portfolio", 12000.0, "paper")
]

for name, capital, mode in portfolios_to_create:
    if name not in existing_portfolios:
        db.add_portfolio(name, capital, mode)
        print(f"✔ Created Portfolio: {name}")
    else:
        print(f"🔄 Portfolio '{name}' already exists.")

# Retrieve updated portfolio IDs
portfolios = {p[1]: p[0] for p in db.get_portfolios()}

# ====== Check & Add Stocks to Portfolios ======
print("\n📌 Adding Stocks to Portfolios...")
portfolio_stocks = {
    "Dollar Cost Averaging Portfolio": ["AAPL", "MSFT"],
    "Growth Portfolio": ["TSLA", "NVDA"],
    "Value Investing Portfolio": ["KO", "JNJ"]
}

for portfolio_name, stocks in portfolio_stocks.items():
    portfolio_id = portfolios[portfolio_name]
    existing_stocks = {s[2] for s in db.get_stocks(portfolio_id)}

    for stock in stocks:
        if stock not in existing_stocks:
            db.add_stock(portfolio_id, stock)
            print(f"✔ Added {stock} to {portfolio_name}")
        else:
            print(f"🔄 {stock} already exists in {portfolio_name}")

# ====== Check & Add Strategies ======
print("\n📌 Adding Strategies...")

existing_strategies = {s["name"] for s in db.get_strategies()}
strategies_to_create = [
    ("Dollar Cost Averaging", {"interval": "monthly", "investment": 500}, ["Dollar Cost Averaging Portfolio"]),
    ("Momentum Breakout", {
        "indicators": [
            {"type": "RSI", "parameters": {"period": 14}, "condition": "<", "value": 30},
            {"type": "Moving Average", "parameters": {"period": 50}, "condition": "crosses_above",
             "reference": "Moving Average", "reference_parameters": {"period": 200}}
        ],
        "entry_condition": "all",
        "exit_condition": {"type": "RSI", "parameters": {"period": 14}, "condition": ">", "value": 70},
        "risk_management": {"stop_loss": 2.0, "take_profit": 5.0, "position_size": 0.05}
    }, ["Growth Portfolio", "Value Investing Portfolio"]),
    ("Value Investing", {"pe_ratio": 15, "dividend_yield": 4.5}, ["Value Investing Portfolio"])
]

for name, parameters, linked_portfolios in strategies_to_create:
    if name not in existing_strategies:
        linked_portfolio_ids = [portfolios[p] for p in linked_portfolios]
        db.add_strategy(name, parameters, portfolio_ids=linked_portfolio_ids)
        print(f"✔ Created Strategy: {name}")
    else:
        print(f"🔄 Strategy '{name}' already exists.")

# ====== Generate AI-Based Strategy & Store ======
print("\n📌 Generating AI-Powered Trading Strategy...")
user_request = "Create a value trading strategy using fundamental metrics and momentum indicator."
strategy_json = generate_trading_strategy(user_request)

if "error" not in strategy_json:
    strategy_name = strategy_json["strategy_name"]
    if strategy_name not in existing_strategies:
        db.add_strategy(strategy_name, strategy_json, portfolio_ids=[portfolios["Value Investing Portfolio"]])
        print(f"✔ AI-Generated Strategy Added: {strategy_name}")
    else:
        print(f"🔄 AI Strategy '{strategy_name}' already exists.")

# ====== Check & Add Stock Screens ======
print("\n📌 Adding Stock Screens...")

existing_screens = {s["name"] for s in db.get_stock_screens()}
stock_screens_to_create = [
    ("High Dividend Stocks", {"sector": "Financials", "dividend_yield": {"min": 5}}, 10, ["Value Investing Portfolio"]),
    ("Growth Stocks", {"revenue_growth_yoy": {"min": 10}, "pe_ratio": {"max": 30}}, 20, ["Growth Portfolio"]),
    ("Tech Leaders", {"sector": "Technology", "market_cap": {"min": 50000000000}}, 15, ["Growth Portfolio"]),
    ("Blue Chip Value Stocks", {"pe_ratio": {"max": 15}, "dividend_yield": {"min": 3}}, 10, ["Value Investing Portfolio"])
]

for name, criteria, stock_limit, linked_portfolios in stock_screens_to_create:
    if name not in existing_screens:
        db.add_stock_screen(name, criteria, stock_limit)
        print(f"✔ Created Stock Screen: {name}")

        # Retrieve the new screen ID
        screen_id = next(s["id"] for s in db.get_stock_screens() if s["name"] == name)
        
        # Link to portfolios
        for portfolio in linked_portfolios:
            portfolio_id = portfolios[portfolio]
            db.link_screen_to_portfolio(portfolio_id, screen_id)
            print(f"🔗 Linked '{name}' to {portfolio}")

    else:
        print(f"🔄 Stock Screen '{name}' already exists.")

# ====== Summary ======
print("\n📊 Summary of Created Elements:")
print(f"✔ Total Portfolios: {len(portfolios)}")
print(f"✔ Total Strategies: {len(db.get_strategies())}")
print(f"✔ Total Stock Screens: {len(db.get_stock_screens())}")

# Close database connection
db.close_connection()
print("\n✅ Example Portfolios, Strategies & Stock Screens Successfully Setup!")
