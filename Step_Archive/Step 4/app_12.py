import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from datetime import date

# Your local modules
from database import TradingDatabase
from chatgpt_api import generate_trading_strategy
from data_fetcher import StockDataFetcher
from ftse_fetcher import FTSETickerFetcher

def main():
    # Initialize the database and set up the page
    db = TradingDatabase()
    st.set_page_config(page_title="Combined Trading Dashboard", layout="wide")
    st.title("📊 Combined Trading Dashboard")

    # Create the TABS
    tab_mgmt, tab_overview, tab_history, tab_compare, tab_strategy, tab_ftse, tab_price = st.tabs([
        "Portfolio Management",
        "Portfolio Overview",
        "Trade History & Filtering",
        "Compare Portfolios",
        "AI-Powered Trading Strategies",
        "Manage Tickers & Fundamentals",
        "View & Fetch Price Data"
    ])

    # -------------------------------------------------------------------------
    # HELPER: Load all portfolios + dictionary
    # -------------------------------------------------------------------------
    def load_portfolios():
        pf = db.get_portfolios()
        pf_dict = {p[0]: f"{p[1]} (${p[2]:,.2f}) - {p[3]}" for p in pf}
        return pf, pf_dict

    portfolios, portfolio_dict = load_portfolios()
    portfolio_ids = list(portfolio_dict.keys())

    # -------------------------------------------------------------------------
    # SIDEBAR: Select portfolio + quick summary
    # -------------------------------------------------------------------------
    st.sidebar.header("Selected Portfolio")

    if portfolios:
        selected_portfolio_id = st.sidebar.selectbox(
            "Select a Portfolio",
            portfolio_ids,
            format_func=lambda x: portfolio_dict[x],
        )

        # Quick summary in the sidebar
        portfolio_value = db.calculate_portfolio_value(selected_portfolio_id)
        initial_capital = next(p[2] for p in portfolios if p[0] == selected_portfolio_id)
        return_percentage = (
            ((portfolio_value - initial_capital) / initial_capital) * 100
            if initial_capital > 0
            else 0
        )
        st.sidebar.markdown(
            f"**Value:** ${portfolio_value:,.2f}\n\n**Return:** {return_percentage:.2f}%"
        )
    else:
        st.sidebar.warning("No portfolios found. Please create one in the 'Portfolio Management' tab.")
        selected_portfolio_id = None

    # =========================================================================
    # TAB 1: Portfolio Management
    # =========================================================================
    with tab_mgmt:
        st.subheader("Manage Portfolios")

        # Create new portfolio
        st.write("### Create a New Portfolio")
        new_name = st.text_input("Portfolio Name", key="new_portfolio_name")
        new_capital = st.number_input("Initial Capital", min_value=0.0, step=100.0, key="new_portfolio_capital")
        new_mode = st.selectbox("Execution Mode", ["paper", "live"], key="new_portfolio_mode")

        if st.button("Add Portfolio"):
            if new_name and new_capital > 0:
                db.add_portfolio(new_name, new_capital, new_mode)
                st.success(f"Portfolio '{new_name}' added!")
                st.rerun()

        # Delete selected portfolio
        st.write("### Delete a Portfolio")
        if portfolios:
            del_port_id = st.selectbox(
                "Select Portfolio to Delete",
                portfolio_ids,
                format_func=lambda x: portfolio_dict[x],
                key="delete_portfolio_select"
            )
            if st.button("Delete Selected Portfolio"):
                db.delete_portfolio(del_port_id)
                st.warning(f"Portfolio {del_port_id} deleted!")
                st.rerun()
        else:
            st.info("No portfolios to delete.")

        # Optionally Clean Database
        st.write("### Database Maintenance")
        if st.button("Clean Database (Remove Orphans)"):
            db.clean_database()
            st.success("Database cleaned!")

    # =========================================================================
    # TAB 2: Portfolio Overview
    # =========================================================================
    with tab_overview:
        st.subheader("Portfolio Overview")
        if selected_portfolio_id is not None:
            # Recompute in case of changes
            portfolio_value = db.calculate_portfolio_value(selected_portfolio_id)
            initial_capital = next(p[2] for p in portfolios if p[0] == selected_portfolio_id)
            return_percentage = (
                ((portfolio_value - initial_capital) / initial_capital) * 100
                if initial_capital > 0
                else 0
            )

            trades = db.get_trades(selected_portfolio_id)
            if trades:
                df_trades = pd.DataFrame(
                    trades,
                    columns=[
                        "ID",
                        "Portfolio ID",
                        "Stock",
                        "Type",
                        "Quantity",
                        "Price",
                        "Transaction Cost",
                        "Timestamp",
                    ],
                )
                df_trades["Timestamp"] = pd.to_datetime(df_trades["Timestamp"])
                df_trades.sort_values("Timestamp", inplace=True)

                # Calculate totals for each trade
                df_trades["Total Cost"] = df_trades["Quantity"] * df_trades["Price"] + df_trades["Transaction Cost"]

                # Cumulative Return
                df_trades["Cumulative Return"] = df_trades["Total Cost"].cumsum()

                # Sharpe Ratio
                returns = df_trades["Cumulative Return"].pct_change().dropna()
                sharpe_ratio = np.mean(returns) / np.std(returns) if not returns.empty else 0

                # Drawdown Calculation
                cumulative_max = df_trades["Cumulative Return"].cummax()
                drawdown = df_trades["Cumulative Return"] - cumulative_max
                max_drawdown = drawdown.min()
            else:
                sharpe_ratio = 0
                max_drawdown = 0

            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="💰 Portfolio Value", value=f"${portfolio_value:,.2f}")
                st.metric(label="📈 Portfolio Return", value=f"{return_percentage:.2f}%")

            with col2:
                st.write("#### Key Performance Metrics")
                st.write(f"- Initial Capital: **${initial_capital:,.2f}**")
                st.write(f"- Current Value: **${portfolio_value:,.2f}**")
                st.write(f"- Total Return: **{return_percentage:.2f}%**")
                if trades:
                    st.write(f"- Max Drawdown: **${max_drawdown:,.2f}**")
                    st.write(f"- Sharpe Ratio: **{sharpe_ratio:.2f}**")
        else:
            st.info("No portfolio selected. Please choose one on the left sidebar.")

    # =========================================================================
    # TAB 3: Trade History & Filtering
    # =========================================================================
    with tab_history:
        st.subheader("Trade History & Filtering")

        if selected_portfolio_id is not None:
            trades = db.get_trades(selected_portfolio_id)
            if trades:
                df_trades = pd.DataFrame(
                    trades,
                    columns=[
                        "Trade ID",
                        "Portfolio ID",
                        "Stock",
                        "Type",
                        "Quantity",
                        "Price",
                        "Transaction Cost",
                        "Timestamp",
                    ],
                )
                df_trades["Timestamp"] = pd.to_datetime(df_trades["Timestamp"])
                df_trades.sort_values("Timestamp", inplace=True)

                start_date = st.date_input("Start Date", df_trades["Timestamp"].min().date())
                end_date = st.date_input("End Date", df_trades["Timestamp"].max().date())

                filtered_df = df_trades[
                    (df_trades["Timestamp"].dt.date >= start_date) 
                    & (df_trades["Timestamp"].dt.date <= end_date)
                ]

                st.dataframe(filtered_df.drop(columns=["Portfolio ID"]))

                # Export to CSV
                csv_data = filtered_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Filtered Trades as CSV",
                    data=csv_data,
                    file_name=f"trade_history_{selected_portfolio_id}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No trades found for this portfolio.")

            st.write("---")
            st.write("### Add a New Trade")
            # Form to add trades
            with st.form(key="add_trade_form"):
                stock_ticker = st.text_input("Stock Ticker", "")
                trade_type = st.selectbox("Trade Type", ["buy", "sell"])
                quantity = st.number_input("Quantity", min_value=1, step=1)
                price = st.number_input("Price", min_value=0.0, step=1.0)
                transaction_cost = st.number_input("Transaction Cost", min_value=0.0, step=1.0)
                submitted = st.form_submit_button("Add Trade")
                if submitted:
                    db.add_trade(
                        portfolio_id=selected_portfolio_id,
                        stock_ticker=stock_ticker,
                        trade_type=trade_type,
                        quantity=quantity,
                        price=price,
                        transaction_cost=transaction_cost,
                    )
                    st.success("Trade added successfully!")
                    st.rerun()

            # Remove trade
            if trades:
                st.write("### Remove a Trade")
                trade_ids = [t[0] for t in trades]  # trade ID is the first column
                remove_id = st.selectbox("Select Trade to Remove", trade_ids)
                if st.button("Remove Trade"):
                    db.delete_trade(remove_id)
                    st.warning(f"Trade {remove_id} removed!")
                    st.rerun()
        else:
            st.info("No portfolio selected. Please choose one on the left sidebar.")

    # =========================================================================
    # TAB 4: Compare Portfolios
    # =========================================================================
    with tab_compare:
        st.subheader("Compare Portfolio Performance")

        if portfolios:
            selected_portfolios = st.multiselect(
                "Select Portfolios to Compare",
                list(portfolio_dict.keys()),
                format_func=lambda x: portfolio_dict[x],
            )
            if selected_portfolios:
                portfolio_values = {
                    pid: db.calculate_portfolio_value(pid) for pid in selected_portfolios
                }
                df_comparison = pd.DataFrame(
                    list(portfolio_values.items()), columns=["Portfolio ID", "Portfolio Value"]
                )
                df_comparison["Portfolio Name"] = df_comparison["Portfolio ID"].apply(
                    lambda x: portfolio_dict[x]
                )

                fig, ax = plt.subplots()
                ax.bar(
                    df_comparison["Portfolio Name"],
                    df_comparison["Portfolio Value"],
                    color="skyblue",
                )
                ax.set_xlabel("Portfolios")
                ax.set_ylabel("Portfolio Value ($)")
                ax.set_title("Portfolio Value Comparison")
                st.pyplot(fig)
            else:
                st.info("Select at least one portfolio to compare.")
        else:
            st.info("No portfolios available to compare.")

    # =========================================================================
    # TAB 5: AI-Powered Trading Strategies
    # =========================================================================
    with tab_strategy:
        st.subheader("AI-Powered Trading Strategies")

        # Make sure 'strategy' exists in session_state
        if "strategy" not in st.session_state:
            st.session_state["strategy"] = None

        user_strategy_input = st.text_area(
            "Describe your trading strategy in plain English:",
            placeholder="Example: Create a breakout strategy using RSI and MACD."
        )

        if st.button("Generate Strategy"):
            if user_strategy_input.strip():
                # Generate and store in session_state
                generated_strategy = generate_trading_strategy(user_strategy_input)
                st.session_state["strategy"] = generated_strategy
                st.json(generated_strategy)  # Show the result
            else:
                st.warning("Please enter a trading idea.")

        # Assign & Save Strategy
        if st.session_state["strategy"] is not None:
            st.write("### Assign and Save Strategy")

            # Refresh the list of portfolios in case user created a new one
            portfolios_for_assign, pf_dict_for_assign = load_portfolios()
            if portfolios_for_assign:
                selected_portfolio_id_for_strategy = st.selectbox(
                    "Assign Strategy to Portfolio",
                    [p[0] for p in portfolios_for_assign],
                    format_func=lambda pid: pf_dict_for_assign[pid],
                )
                if st.button("Save Strategy to Database"):
                    # Actually save it
                    name = st.session_state["strategy"].get("strategy_name", "Untitled Strategy")
                    db.add_strategy(name, st.session_state["strategy"], [selected_portfolio_id_for_strategy])
                    st.success(f"Strategy '{name}' saved successfully!")
                    # Optionally clear so user doesn't keep re-saving:
                    st.session_state["strategy"] = None
            else:
                st.warning("No portfolios available for assignment. Please create one first.")

        # View and Edit Existing Strategies
        if portfolios and selected_portfolio_id is not None:
            st.write("### Existing Strategies for Current Portfolio")
            strategies = db.get_portfolio_strategies(selected_portfolio_id)
            if strategies:
                for sdict in strategies:
                    strategy_id = sdict.get("id")
                    strategy_name = sdict.get("name")
                    strategy_parameters = sdict.get("parameters")

                    with st.expander(f"{strategy_name}"):
                        st.json(strategy_parameters)  # Show full details
                        updated_strategy_text = st.text_area(
                            "Modify Strategy JSON",
                            value=str(strategy_parameters)
                        )
                        if st.button(f"Update {strategy_name}"):
                            db.update_strategy(strategy_id, updated_strategy_text)
                            st.success("Strategy updated successfully!")
            else:
                st.info("No strategies found for this portfolio.")

   # =========================================================================
    # TAB 6: Manage Tickers & Fundamentals
    # =========================================================================
    with tab_ftse:
        st.header("Step A: Scrape & Store FTSE Tickers")

        # FTSETickerFetcher now JUST fetches tickers, no force_update logic
        fetcher_ftse = FTSETickerFetcher()  # no DB or force_update references
        fetcher_data = StockDataFetcher(db)  # for fundamentals

        # 1. Scrape Tickers from Wikipedia
        if st.button("Scrape FTSE Tickers"):
            with st.spinner("Scraping..."):
                # Call get_all_ftse_index_tickers() WITHOUT any force_update param
                all_tickers_dict = fetcher_ftse.get_all_ftse_index_tickers()
                st.session_state["all_tickers_dict"] = all_tickers_dict

            st.success("Scraped FTSE Tickers Successfully!")
            # Show results
            for index_name, tlist in st.session_state["all_tickers_dict"].items():
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
                        db.add_master_stock(t)  # store the ticker in stocks table
                        total_count += 1
                st.success(f"Stored {total_count} tickers in DB.")

        st.write("---")
        st.header("Step B: Fetch Fundamentals for All DB Tickers")

        # Checkbox for forcing fundamentals updates (belongs to StockDataFetcher, not FTSE fetcher)
        force_refresh = st.checkbox("Force Update Fundamentals (Ignore 7-day rule)?", value=False)

        st.write("Click the button below to download fundamentals for all tickers in `stocks` table.")
        if st.button("Fetch Fundamentals for All Tickers in DB"):
            db.cursor.execute("SELECT ticker FROM stocks")
            db_tickers = [row[0] for row in db.cursor.fetchall()]

            if not db_tickers:
                st.warning("No tickers found in DB. Please store some first.")
            else:
                progress_bar = st.progress(0)
                total = len(db_tickers)
                for i, ticker in enumerate(db_tickers, start=1):
                    # Pass force_refresh to fetch_fundamental_data 
                    fetcher_data.fetch_fundamental_data(ticker, force_refresh=force_refresh)
                    progress_bar.progress(int((i / total) * 100))
                    # time.sleep(0.1)

                st.success(f"Fetched fundamentals for {total} tickers.")

        st.write("---")
        st.subheader("View Fundamentals for a Specific Ticker in DB")
        db.cursor.execute("SELECT ticker FROM stocks ORDER BY ticker ASC")
        db_tickers_for_view = [row[0] for row in db.cursor.fetchall()]
        if db_tickers_for_view:
            chosen_ticker = st.selectbox("Choose a ticker to view fundamentals:", db_tickers_for_view)
            if chosen_ticker:
                row = db.get_fundamentals(chosen_ticker)
                if row:
                    # columns in the same order as your extended schema
                    fundamental_cols = [
                        "id", "ticker", "market_cap", "pe_ratio", "eps", 
                        "dividend_yield", "debt_to_equity", "last_updated",
                        "forward_pe", "price_to_book", "price_to_sales", 
                        "enterprise_to_ebitda", "price_to_fcf",
                        "net_profit_margin", "return_on_equity", "return_on_assets", 
                        "return_on_invested_capital", "eps_growth", "revenue_growth_yoy",
                        "earnings_growth_yoy", "revenue_growth_3y", "eps_growth_3y",
                        "dividend_payout_ratio", "dividend_growth_5y", "current_ratio", 
                        "quick_ratio", "interest_coverage", "free_float", 
                        "insider_ownership", "institutional_ownership", "beta", 
                        "price_change_52w"
                    ]
                    fundamentals_dict = dict(zip(fundamental_cols, row))
                    st.json(fundamentals_dict)
                else:
                    st.info(f"No fundamental data found yet for {chosen_ticker}.")
        else:
            st.info("No tickers in DB yet. Scrape & store them first.")

    # =========================================================================
    # TAB 7: View & Fetch Price Data (From app_11)
    # =========================================================================
    with tab_price:
        st.header("Fetch & View Price Data for a Ticker")
        fetcher_data = StockDataFetcher(db)

        # Let user pick a ticker from DB or type one
        db.cursor.execute("SELECT ticker FROM stocks ORDER BY ticker ASC")
        db_tickers_for_price = [row[0] for row in db.cursor.fetchall()]

        chosen_ticker2 = ""
        if db_tickers_for_price:
            chosen_ticker2 = st.selectbox("Choose a ticker to fetch/view price data:", [""] + db_tickers_for_price)
        
        typed_ticker = st.text_input("Or type a ticker manually (e.g. 'VOD.L'):")

        # Decide which ticker to use
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
                    price_rows = db.get_price_data(final_ticker)
                    if not price_rows:
                        st.info("No price data found in DB. Fetch first.")
                    else:
                        p_cols = ["date", "open_price", "high_price", "low_price",
                                  "close_price", "adjusted_close", "volume"]
                        df_prices = pd.DataFrame(price_rows, columns=p_cols)

                        st.dataframe(df_prices.head(10))

                        df_prices["date"] = pd.to_datetime(df_prices["date"])
                        df_prices.set_index("date", inplace=True)

                        st.line_chart(df_prices["close_price"], height=300)

    # -------------------------------------------------------------------------
    # Close DB connection at the end
    # -------------------------------------------------------------------------
    db.close_connection()

if __name__ == "__main__":
    main()
