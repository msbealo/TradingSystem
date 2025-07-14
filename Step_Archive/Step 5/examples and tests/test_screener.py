import json
from database import TradingDatabase

def main():
    db = TradingDatabase()
    print("🔄 Starting Stock Screener Test...")

    # 1) Ensure we have a test portfolio
    #    We'll try to find a portfolio named "Test Portfolio",
    #    or create it if it doesn't exist.
    portfolio_name = "Test Portfolio"
    portfolio_id = get_or_create_portfolio(db, portfolio_name, capital=10000.0)

    # 2) Create a sample stock screen 
    #    This example looks for companies with market_cap >= 1e9, P/E <= 20
    #    You can adapt the criteria to your environment or data.
    screen_name = "Test Screener"
    criteria = {
        "market_cap": {"min": 1e9},   # e.g. >= 1 billion
        "pe_ratio":   {"max": 20}     # e.g. <= 20
    }
    create_or_update_screen(db, screen_name, criteria, stock_limit=10)

    # 3) Apply the screen & see which stocks match
    screen_info = get_screen_by_name(db, screen_name)
    if not screen_info:
        print(f"❌ Could not find the screen '{screen_name}'!")
        return
    screen_id = screen_info["id"]

    applied_result = db.apply_stock_screen(screen_id)
    results = applied_result.get("results", [])
    ignored = applied_result.get("ignored_filters", [])

    print("🔎 Applied Screen Results:")
    print(f"• Found {len(results)} matching stocks.")
    if ignored:
        print(f"• Ignored filters: {ignored}")

    if not results:
        print("No stocks found for this screen. Nothing to add.")
        return

    # 4) Pick the first matching stock (or random, if you prefer) & add it to the portfolio
    first_stock = results[0]["ticker"]
    print(f"• Adding ticker '{first_stock}' to portfolio '{portfolio_name}' (ID {portfolio_id}).")
    db.add_stock(portfolio_id, first_stock)

    # 5) Verify that the stock was added
    portfolio_stocks = db.get_stocks(portfolio_id)
    tickers_in_portfolio = [row[2] for row in portfolio_stocks]  # row format: (id, portfolio_id, stock_ticker)
    if first_stock in tickers_in_portfolio:
        print(f"✅ Stock '{first_stock}' is now in the portfolio.")
    else:
        print(f"❌ Stock '{first_stock}' was NOT added successfully!")

    db.close_connection()
    print("🎉 Test Completed.")

def get_or_create_portfolio(db: TradingDatabase, name: str, capital: float) -> int:
    """
    Checks if a portfolio with this name exists. If not, creates it.
    Returns the portfolio's ID.
    """
    # Retrieve all existing
    all_pf = db.get_portfolios()
    # all_pf is like [ (id, name, capital, mode), (id, name, capital, mode), ...]
    for p in all_pf:
        if p[1] == name:
            print(f"🔄 Portfolio '{name}' already exists with ID {p[0]}.")
            return p[0]
    # Otherwise create
    print(f"• Creating new portfolio '{name}' with capital={capital}.")
    db.add_portfolio(name, capital, "paper")  # default to "paper"
    # fetch newly created
    updated_pf = db.get_portfolios()
    for p in updated_pf:
        if p[1] == name:
            return p[0]
    raise RuntimeError("Failed to create portfolio")

def create_or_update_screen(db: TradingDatabase, screen_name: str, criteria: dict, stock_limit=None):
    """
    Checks if a screen with `screen_name` exists. 
    If it does, update its criteria; if not, create a new one.
    """
    screens = db.get_stock_screens()
    for s in screens:
        if s["name"] == screen_name:
            print(f"🔄 Screen '{screen_name}' already exists. Updating criteria.")
            db.update_stock_screen(s["id"], screen_name, criteria, stock_limit)
            return
    # Otherwise, create a new screen
    print(f"• Creating new screen '{screen_name}' with limit={stock_limit}.")
    db.add_stock_screen(screen_name, criteria, stock_limit)

def get_screen_by_name(db: TradingDatabase, screen_name: str):
    """
    Returns the screen dict with this name, or None if not found.
    """
    screens = db.get_stock_screens()
    for s in screens:
        if s["name"] == screen_name:
            return s
    return None


if __name__ == "__main__":
    main()
