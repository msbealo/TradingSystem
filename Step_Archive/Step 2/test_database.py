from database import TradingDatabase  # Import the TradingDatabase class

def test_trading_database():
    print("\n===== TESTING TRADING DATABASE FUNCTIONS =====\n")

    # ✅ Initialize Database
    db = TradingDatabase()

    # ✅ CLEAN UP EXISTING DATA BEFORE TESTING
    print("Cleaning up existing database...")
    db.clean_database()

    # Delete all existing portfolios to avoid duplicates
    portfolios = db.get_portfolios()
    for portfolio in portfolios:
        db.delete_portfolio(portfolio[0])

    print("Database reset complete.")

    # ✅ 1. Create a Single Portfolio
    print("\nAdding portfolio...")
    db.add_portfolio("Test Portfolio", 10000.0, "paper")

    # Fetch the newly created portfolio ID
    portfolio_id = db.get_portfolios()[0][0]
    print(f"Using Portfolio ID: {portfolio_id}")

    # ✅ 2. Add Stocks to Portfolio
    print("\nAdding stocks...")
    db.add_stock(portfolio_id, "AAPL")
    db.add_stock(portfolio_id, "TSLA")

    # ✅ 3. Add Strategy
    print("\nAdding strategy...")
    db.add_strategy(portfolio_id, "Momentum Strategy", {"rsi_threshold": 30, "macd_signal": 9})

    # ✅ 4. Log Trades (Ensure No Duplicates)
    print("\nLogging trades...")
    db.add_trade(portfolio_id, "AAPL", "buy", 10, 150.25, transaction_cost=1.5)
    db.add_trade(portfolio_id, "TSLA", "sell", 5, 800.50, transaction_cost=2.0)

    # ✅ 5. Calculate Portfolio Value
    print("\nCalculating portfolio value...")
    portfolio_value = db.calculate_portfolio_value(portfolio_id)
    print(f"Portfolio Value: {portfolio_value}")

    # ✅ 6. Verify Database Consistency
    print("\nCurrent Portfolios:", db.get_portfolios())
    print("Current Stocks:", db.get_stocks())
    print("Current Strategies:", db.get_strategies())
    print("Current Trades:", db.get_trades())

    # ✅ 7. Clean Up and Close Connection
    db.clean_database()
    db.close_connection()
    print("\n===== DATABASE TESTS COMPLETED SUCCESSFULLY =====\n")

# Run the test script
if __name__ == "__main__":
    test_trading_database()
