import datetime
from database import TradingDatabase  # Import the TradingDatabase class

# Initialize the database
db = TradingDatabase()

# ====== Create Portfolios ======
print("📌 Creating Portfolios...")
db.add_portfolio("Dollar Cost Averaging Portfolio", 10000.0, "paper")
db.add_portfolio("Growth Portfolio", 15000.0, "paper")
db.add_portfolio("Value Investing Portfolio", 12000.0, "paper")

# Retrieve portfolio IDs
portfolios = db.get_portfolios()
dca_portfolio_id = portfolios[0][0]
growth_portfolio_id = portfolios[1][0]
value_portfolio_id = portfolios[2][0]

# ====== Add Stocks to Portfolios ======
print("📌 Adding Stocks to Portfolios...")
db.add_stock(dca_portfolio_id, "AAPL")  # Apple for DCA
db.add_stock(dca_portfolio_id, "MSFT")  # Microsoft for DCA
db.add_stock(growth_portfolio_id, "TSLA")  # Tesla for Growth
db.add_stock(growth_portfolio_id, "NVDA")  # Nvidia for Growth
db.add_stock(value_portfolio_id, "KO")  # Coca-Cola for Value Investing
db.add_stock(value_portfolio_id, "JNJ")  # Johnson & Johnson for Value Investing

# ====== Add Strategies and Apply to Multiple Portfolios ======
print("📌 Adding Strategies...")

db.add_strategy(
    "Dollar Cost Averaging",
    {
        "interval": "monthly",
        "investment": 500
    },
    portfolio_ids=[dca_portfolio_id]  # This strategy applies only to DCA portfolio
)

db.add_strategy(
    "Momentum Breakout",
    {
        "indicators": [
            {"type": "RSI", "parameters": {"period": 14}, "condition": "<", "value": 30},
            {"type": "Moving Average", "parameters": {"period": 50}, "condition": "crosses_above", "reference": "Moving Average", "reference_parameters": {"period": 200}}
        ],
        "entry_condition": "all",
        "exit_condition": {"type": "RSI", "parameters": {"period": 14}, "condition": ">", "value": 70},
        "risk_management": {"stop_loss": 2.0, "take_profit": 5.0, "position_size": 0.05}
    },
    portfolio_ids=[growth_portfolio_id, value_portfolio_id]  # Applied to both Growth and Value Investing portfolios
)

db.add_strategy(
    "Value Investing",
    {
        "pe_ratio": 15,
        "dividend_yield": 4.5
    },
    portfolio_ids=[value_portfolio_id]  # Applied only to the Value Investing portfolio
)

# ====== Simulate Trades Over Time ======
print("📌 Logging Trades Over Time...")

# Simulated dates
start_date = datetime.datetime(2023, 1, 1)

# 📌 Dollar-Cost Averaging Portfolio (Buys Monthly)
for i in range(12):
    trade_date = start_date + datetime.timedelta(days=30 * i)
    db.add_trade(dca_portfolio_id, "AAPL", "buy", 5, 140 + i * 2, 1.0)  # Buying AAPL at increasing price
    db.add_trade(dca_portfolio_id, "MSFT", "buy", 4, 250 + i * 3, 1.2)  # Buying MSFT at increasing price

# 📌 Growth Portfolio (Well-Timed Trades)
db.add_trade(growth_portfolio_id, "TSLA", "buy", 10, 220, 2.5)  # Buy Tesla at $220
db.add_trade(growth_portfolio_id, "TSLA", "sell", 10, 350, 3.0)  # Sell Tesla at $350 (Nice profit)
db.add_trade(growth_portfolio_id, "NVDA", "buy", 8, 190, 1.8)  # Buy Nvidia at $190
db.add_trade(growth_portfolio_id, "NVDA", "sell", 8, 280, 2.0)  # Sell Nvidia at $280 (Good trade)

# 📌 Value Investing Portfolio (Buying Strong Dividend Stocks)
db.add_trade(value_portfolio_id, "KO", "buy", 15, 55, 1.0)  # Buy Coca-Cola at $55
db.add_trade(value_portfolio_id, "KO", "buy", 10, 52, 1.2)  # Buy more at a dip
db.add_trade(value_portfolio_id, "JNJ", "buy", 8, 160, 1.5)  # Buy J&J at $160
db.add_trade(value_portfolio_id, "JNJ", "sell", 8, 185, 2.0)  # Sell J&J at $185 (Profitable trade)

# ====== Retrieve & Display Strategies for Each Portfolio ======
print("\n📌 Strategies Linked to Each Portfolio:")
for p_id, name in [(dca_portfolio_id, "Dollar-Cost Averaging"), (growth_portfolio_id, "Growth"), (value_portfolio_id, "Value Investing")]:
    strategies = db.get_portfolio_strategies(p_id)
    print(f"\n📊 {name} Portfolio Strategies:")
    for strategy in strategies:
        print(f"✔ {strategy['name']} → {strategy['parameters']}")

# ====== Final Portfolio Value Calculation ======
print("\n📊 Portfolio Values After Trades:")
for p_id, name in [(dca_portfolio_id, "Dollar-Cost Averaging"), (growth_portfolio_id, "Growth"), (value_portfolio_id, "Value Investing")]:
    value = db.calculate_portfolio_value(p_id)
    print(f"✔ {name} Portfolio Value: ${value:,.2f}")

# Close database connection
db.close_connection()
print("\n✅ Example Portfolios & Trades Successfully Setup!")
