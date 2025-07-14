# app_get_ftse.py

import streamlit as st
from database import TradingDatabase
from ftse_fetcher import FTSETickerFetcher

def main():
    st.title("FTSE Ticker Fetcher Demo")

    fetcher = FTSETickerFetcher()
    db = TradingDatabase()

    if st.button("Get FTSE Tickers"):
        # 1. Retrieve the dictionary of { index_name: [tickers] }
        all_tickers = fetcher.get_all_ftse_index_tickers()
        
        # 2. Display them in the UI
        for index_name, ticker_list in all_tickers.items():
            st.write(f"**{index_name}** ({len(ticker_list)} tickers):", ticker_list)

    if st.button("Store Tickers in DB"):
        # Typically you'd do: 
        all_tickers = fetcher.get_all_ftse_index_tickers()
        for index_name, ticker_list in all_tickers.items():
            st.write(f"Storing {len(ticker_list)} tickers for {index_name} in DB...")
            for t in ticker_list:
                # e.g., store in your 'stocks' table
                db.add_master_stock(t)
        st.success("All FTSE tickers have been stored in the DB.")

    db.close_connection()

if __name__ == "__main__":
    main()
