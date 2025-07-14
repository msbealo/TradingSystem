# test_ftse.py

import sys
import os
import datetime

# If needed, adjust PYTHONPATH so Python can find your local modules
# For example, if they're in a folder named 'src' or 'trading_system':
# sys.path.append(os.path.abspath("src"))

from database import TradingDatabase
from ftse_fetcher import FTSETickerFetcher

def main():
    print("=== TEST: FTSETickerFetcher ===")

    # 1. Initialize the database
    db = TradingDatabase()
    print("Database initialized.")

    # 2. Create an instance of FTSETickerFetcher, passing in the DB
    fetcher = FTSETickerFetcher(db)
    print("FTSETickerFetcher created.")

    # 3. Call get_all_ftse_index_tickers
    #    - If you want to skip tickers that have fresh (<7 days) fundamentals, set force_update=False
    #    - If you want to forcibly update everything, set force_update=True
    force_update = False
    print(f"Calling fetcher.get_all_ftse_index_tickers(force_update={force_update})...")

    all_tickers_dict = fetcher.get_all_ftse_index_tickers(force_update=force_update)

    # 4. Print the results
    for index_name, tickers in all_tickers_dict.items():
        print(f"\nIndex: {index_name}, Ticker Count: {len(tickers)}")
        print(tickers)

    # 5. (Optional) Store tickers in DB
    #    Uncomment if you want to actually insert them into your 'stocks' table
    store_in_db = False  # set to True to test DB insertion
    if store_in_db:
        total_stored = 0
        for index_name, tlist in all_tickers_dict.items():
            for t in tlist:
                db.add_master_stock(t)
                total_stored += 1
        print(f"\nStored {total_stored} tickers in DB.")

    # 6. Close DB connection
    db.close_connection()
    print("\n=== Finished test_ftse script. ===")

if __name__ == "__main__":
    main()
