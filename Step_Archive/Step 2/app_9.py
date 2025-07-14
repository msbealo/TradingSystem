# app_9.py

import streamlit as st
import pandas as pd
from database import TradingDatabase
from data_fetcher import StockDataFetcher

def main():
    st.title("Extended Fundamentals & Price Data Demo")

    # Initialize DB and Data Fetcher
    db = TradingDatabase()
    fetcher = StockDataFetcher(db)

    # Ticker Input
    ticker_input = st.text_input("Enter a stock ticker (e.g., 'VOD.L'):", "VOD.L")

    # Buttons for fetching data
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Fetch Fundamentals"):
            fetcher.fetch_fundamental_data(ticker_input)
            st.success(f"Fetched fundamentals for {ticker_input}!")
    with col2:
        if st.button("Fetch Price History"):
            fetcher.fetch_price_data(ticker_input, start_date="2020-01-01")
            st.success(f"Fetched price data for {ticker_input}!")

    st.write("---")
    st.subheader("Fundamental Data")

    # Retrieve extended fundamentals from DB
    fundamentals_row = db.get_fundamentals(ticker_input)
    # Below is the order matching your extended fundamentals table
    fundamental_cols = [
        "id", "ticker", 
        "market_cap", "pe_ratio", "eps", "dividend_yield", "debt_to_equity", 
        "last_updated",
        "forward_pe", "price_to_book", "price_to_sales", "enterprise_to_ebitda", "price_to_fcf",
        "net_profit_margin", "return_on_equity", "return_on_assets", "return_on_invested_capital",
        "eps_growth", "revenue_growth_yoy", "earnings_growth_yoy", "revenue_growth_3y", "eps_growth_3y",
        "dividend_payout_ratio", "dividend_growth_5y", "current_ratio", "quick_ratio",
        "interest_coverage", "free_float", "insider_ownership", "institutional_ownership",
        "beta", "price_change_52w"
    ]

    if fundamentals_row:
        # Convert tuple -> dict for easier viewing
        if len(fundamentals_row) < len(fundamental_cols):
            st.warning("Warning: The database record has fewer columns than expected. Make sure your DB schema is updated.")
        else:
            fundamentals_dict = dict(zip(fundamental_cols, fundamentals_row))
            st.json(fundamentals_dict)
    else:
        st.info("No fundamentals found. Please click 'Fetch Fundamentals' above, or verify DB schema.")

    st.write("---")
    st.subheader("Historical Price Data")

    # Retrieve price data from DB
    price_rows = db.get_price_data(ticker_input)
    if price_rows:
        # price_data columns: (date, open_price, high_price, low_price, close_price, adjusted_close, volume)
        p_cols = ["date", "open_price", "high_price", "low_price", "close_price", "adjusted_close", "volume"]
        df_prices = pd.DataFrame(price_rows, columns=p_cols)

        # Show a sample
        st.dataframe(df_prices.head(10))

        # Convert date to datetime for charting
        df_prices["date"] = pd.to_datetime(df_prices["date"])
        df_prices.set_index("date", inplace=True)

        # Simple line chart for close_price
        st.line_chart(df_prices["close_price"], height=300)
    else:
        st.info("No price data found. Please click 'Fetch Price History' above.")

    # Close DB connection when done
    db.close_connection()

if __name__ == "__main__":
    main()
