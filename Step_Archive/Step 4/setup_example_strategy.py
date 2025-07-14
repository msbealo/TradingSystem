from chatgpt_api import generate_trading_strategy
from database import TradingDatabase

# Initialize Database
db = TradingDatabase()

# Get Strategy from ChatGPT
# user_request = "Create a breakout trading strategy using RSI and MACD."
user_request = "Create a value trading strategy using value fundementals and momentum indicator."
strategy_json = generate_trading_strategy(user_request)

if "error" in strategy_json:
    print("⚠️ Strategy generation failed:", strategy_json["error"])
else:
    print("📌 Generated Strategy:", strategy_json)

    # Store strategy and link to portfolios
    db.add_strategy(strategy_json["strategy_name"], strategy_json, portfolio_ids=[1, 2])
    print("✅ Strategy stored successfully!")
