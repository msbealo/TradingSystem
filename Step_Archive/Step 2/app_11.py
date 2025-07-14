import streamlit as st
import pandas as pd
import time

from database import TradingDatabase
from data_fetcher import StockDataFetcher
from ftse_fetcher import FTSETickerFetcher

def main():
    st.title("FTSE Tickers + Fundamentals + Price Data")

    db = TradingDatabase()
    fetcher_ftse = FTSETickerFetcher()  # For scraping FTSE indexes
    fetcher_data = StockDataFetcher(db) # For fundamentals & price data

    # -----------------------------
    # TAB 1: Manage Tickers
    # -----------------------------
    tab1, tab2 = st.tabs(["1) Manage Tickers & Fundamentals", "2) View & Fetch Price Data"])

    # ======================================
    # TAB 1
    # ======================================
    with tab1:
        st.header("Step A: Scrape & Store FTSE Tickers")

        # 1. Scrape Tickers from Wikipedia
        if st.button("Scrape FTSE Tickers"):
            with st.spinner("Scraping..."):
                all_tickers_dict = fetcher_ftse.get_all_ftse_index_tickers()
                st.session_state["all_tickers_dict"] = all_tickers_dict
            st.success("Scraped FTSE Tickers Successfully!")
            # Show results
            for index_name, tlist in all_tickers_dict.items():
                st.write(f"**{index_name}**: {len(tlist)} tickers")
                st.write(tlist)

        # 2. Store Tickers in DB
        if st.button("Store Tickers in DB"):
            atd = st.session_state.get("all_tickers_dict", {})
            if not atd:
                st.warning("No tickers found in session. Scrape them first.")
            else:
                total_count = 0
                for index_name, tlist in atd.items():
                    for t in tlist:
                        db.add_master_stock(t)
                        total_count += 1
                st.success(f"Stored {total_count} tickers in DB.")

        st.write("---")
        st.header("Step B: Fetch Fundamentals for All DB Tickers")

        st.write("Click the button below to download fundamentals for **all** tickers in the `stocks` table.")
        if st.button("Fetch Fundamentals for All Tickers in DB"):
            # 1) Get all tickers from 'stocks' table
            db.cursor.execute("SELECT ticker FROM stocks")
            db_tickers = [row[0] for row in db.cursor.fetchall()]

            if not db_tickers:
                st.warning("No tickers found in DB. Please store some first.")
            else:
                progress_bar = st.progress(0)
                total = len(db_tickers)
                for i, ticker in enumerate(db_tickers, start=1):
                    # fetch fundamentals
                    fetcher_data.fetch_fundamental_data(ticker)
                    # update progress
                    progress_bar.progress(int((i / total) * 100))
                    time.sleep(0.1)  # tiny pause so progress bar updates smoothly

                st.success(f"Fetched fundamentals for {total} tickers.")

        st.write("---")
        st.subheader("View Fundamentals for a Specific Ticker in DB")
        # Let user pick any ticker in DB to view its fundamentals
        db.cursor.execute("SELECT ticker FROM stocks ORDER BY ticker ASC")
        db_tickers_for_view = [row[0] for row in db.cursor.fetchall()]
        if db_tickers_for_view:
            chosen_ticker = st.selectbox("Choose a ticker to view fundamentals:", db_tickers_for_view)
            if chosen_ticker:
                row = db.get_fundamentals(chosen_ticker)
                if row:
                    # define columns in same order as your extended schema
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
                    # convert row -> dict
                    fundamentals_dict = dict(zip(fundamental_cols, row))
                    st.json(fundamentals_dict)
                else:
                    st.info(f"No fundamental data found yet for {chosen_ticker}.")
        else:
            st.info("No tickers in DB yet. Scrape & store them first.")

    # ======================================
    # TAB 2
    # ======================================
    with tab2:
        st.header("Fetch & View Price Data for a Ticker")

        # Let user pick a ticker from DB or type one
        db.cursor.execute("SELECT ticker FROM stocks ORDER BY ticker ASC")
        db_tickers_for_price = [row[0] for row in db.cursor.fetchall()]

        chosen_ticker2 = ""
        if db_tickers_for_price:
            chosen_ticker2 = st.selectbox("Choose a ticker to fetch/view price data:", [""] + db_tickers_for_price)
        
        typed_ticker = st.text_input("Or type a ticker manually (e.g., ABC.L):")

        # Decide which ticker to use
        # If user typed one, let's prioritize that; else use chosen from selectbox
        final_ticker = typed_ticker.strip() if typed_ticker.strip() else chosen_ticker2

        st.write(f"**Current Ticker Selection:** {final_ticker if final_ticker else '(None Selected)'}")

        colA, colB = st.columns(2)
        with colA:
            if st.button("Fetch Price Data"):
                if not final_ticker:
                    st.warning("No ticker selected. Please choose or type a ticker.")
                else:
                    fetcher_data.fetch_price_data(final_ticker, start_date="2020-01-01")
                    st.success(f"Fetched price data for {final_ticker}.")

        with colB:
            if st.button("View Price Data"):
                if not final_ticker:
                    st.warning("No ticker selected. Please choose or type a ticker.")
                else:
                    # get from DB
                    price_rows = db.get_price_data(final_ticker)
                    if not price_rows:
                        st.info("No price data found in DB. Fetch first.")
                    else:
                        p_cols = ["date","open_price","high_price","low_price",
                                  "close_price","adjusted_close","volume"]
                        df_prices = pd.DataFrame(price_rows, columns=p_cols)

                        st.dataframe(df_prices.head(10))

                        df_prices["date"] = pd.to_datetime(df_prices["date"])
                        df_prices.set_index("date", inplace=True)

                        st.line_chart(df_prices["close_price"], height=300)

    db.close_connection()

if __name__ == "__main__":
    main()
