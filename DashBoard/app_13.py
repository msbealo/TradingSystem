import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time
from datetime import date
import json

# Your local modules
from database import TradingDatabase
from chatgpt_api import ChatGPTAPI
from data_fetcher import StockDataFetcher
from ftse_fetcher import FTSETickerFetcher

def main():
    # Initialize the database and set up the page
    db = TradingDatabase()
    chat = ChatGPTAPI()
    
    st.set_page_config(page_title="Combined Trading Dashboard", layout="wide")
    st.title("📊 Combined Trading Dashboard")

    # Create the TABS (added "Stock Screener" as the 8th tab)
    tab_mgmt, tab_overview, tab_history, tab_compare, tab_strategy, tab_ftse, tab_price, tab_screener = st.tabs([
        "Portfolio Management",
        "Portfolio Overview",
        "Trade History & Filtering",
        "Compare Portfolios",
        "AI-Powered Trading Strategies",
        "Manage Tickers & Fundamentals",
        "View & Fetch Price Data",
        "Stock Screener"  # NEW TAB
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
    # TAB 1: Portfolio Management (Unchanged from app_12.py)
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
    # TAB 2: Portfolio Overview (Unchanged from app_12.py)
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

            # Retrieve trades for the selected portfolio
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

            # ----------------------------------------------------
            # NEW SECTION: Manage Portfolio Stocks (No Trades)
            # ----------------------------------------------------
            st.write("---")
            st.subheader("Manage Stocks in This Portfolio (No Trades)")

            # Retrieve current portfolio stocks (from portfolio_stocks table)
            port_stocks = db.get_stocks(selected_portfolio_id)  # returns e.g. [(id, portfolio_id, "AAPL"), ...]
            if port_stocks:
                # Convert to DataFrame for easy display
                df_stocks = pd.DataFrame(port_stocks, columns=["ID", "Portfolio ID", "Ticker"])
                
                st.markdown("**Current Stocks in Portfolio:**")
                st.dataframe(df_stocks[["ID", "Ticker"]], use_container_width=True)

                # Remove a Stock
                remove_options = df_stocks["ID"].tolist()
                if remove_options:
                    remove_id = st.selectbox(
                        "Select a Stock (ID) to Remove",
                        remove_options,
                        format_func=lambda x: df_stocks.loc[df_stocks["ID"]==x, "Ticker"].values[0]
                    )
                    if st.button("Remove Selected Stock"):
                        db.delete_stock(remove_id)
                        st.warning("Removed stock from portfolio.")
                        st.rerun()
            else:
                st.info("No stocks currently in this portfolio. Add some below.")

            # Add a New Stock to the Portfolio
            new_ticker = st.text_input("Add a New Stock Ticker to This Portfolio", "")
            if st.button("Add Stock"):
                if new_ticker.strip():
                    db.add_stock(selected_portfolio_id, new_ticker.strip())
                    st.success(f"Added {new_ticker.strip()} to portfolio.")
                    st.rerun()
                else:
                    st.warning("Please enter a valid ticker symbol.")
        else:
            st.info("No portfolio selected. Please choose one on the left sidebar.")


    # =========================================================================
    # TAB 3: Trade History & Filtering (Unchanged from app_12.py)
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
    # TAB 4: Compare Portfolios (Unchanged from app_12.py)
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
    # TAB 5: AI-Powered Trading Strategies (Unchanged from app_12.py)
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
                generated_strategy = chat.generate_trading_strategy(user_strategy_input)
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
    # TAB 6: Manage Tickers & Fundamentals (Unchanged from app_12.py)
    # =========================================================================
    with tab_ftse:
        st.header("Step A: Scrape & Store FTSE Tickers")

        fetcher_ftse = FTSETickerFetcher()
        fetcher_data = StockDataFetcher(db)

        # 1. Scrape Tickers from Wikipedia
        if st.button("Scrape FTSE Tickers"):
            with st.spinner("Scraping..."):
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
                        db.add_master_stock(t)
                        total_count += 1
                st.success(f"Stored {total_count} tickers in DB.")

        st.write("---")
        st.header("Step B: Fetch Fundamentals for All DB Tickers")

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
                    fetcher_data.fetch_fundamental_data(ticker, force_refresh=force_refresh)
                    progress_bar.progress(int((i / total) * 100))

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
    # TAB 7: View & Fetch Price Data (Unchanged from app_12.py)
    # =========================================================================
    with tab_price:
        st.header("Fetch & View Price Data for a Ticker")
        fetcher_data = StockDataFetcher(db)

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

    # =========================================================================
    # TAB 8: Stock Screener (UPDATED to use session state)
    # =========================================================================
    with tab_screener:
        st.subheader("Stock Screener")

        # --------------------------------------------------
        # PART 0: ChatGPT-Generated Screener
        # --------------------------------------------------
        st.write("### ChatGPT-Generated Screener")

        # We'll store the AI-generated screener in session state
        if "ai_screener_json" not in st.session_state:
            st.session_state["ai_screener_json"] = None

        user_screener_prompt = st.text_area(
            "Enter plain-English screening criteria:",
            placeholder="Example: 'Find large-cap healthcare stocks with dividend yield over 3% and P/E ratio under 20.'",
            key="user_screener_prompt_key"
        )

        if st.button("Generate Screener via ChatGPT"):
            if user_screener_prompt.strip():
                ai_response = chat.generate_stock_screener(user_screener_prompt.strip())
                if "error" in ai_response:
                    st.error(f"ChatGPT Error: {ai_response['error']}")
                else:
                    # Save to session so we can display & optionally save to DB
                    st.session_state["ai_screener_json"] = ai_response
                    st.success("Below is the AI-generated screener JSON:")
                    st.json(ai_response)
            else:
                st.warning("Please enter your screening criteria in natural language.")

        # If we already have a valid AI screener JSON in session, user can name & save it
        if st.session_state["ai_screener_json"] and "criteria" in st.session_state["ai_screener_json"]:
            st.write("### Save AI-Generated Screener to Database")
            suggested_name = st.text_input("Screen Name", value="AI Screener")  # default name
            if st.button("Save AI Screener"):
                # The AI screener is in st.session_state["ai_screener_json"], e.g.: { "criteria": { ... } }
                screener_criteria = st.session_state["ai_screener_json"]["criteria"]
                db.add_stock_screen(suggested_name, screener_criteria, stock_limit=None)
                st.success(f"Screener '{suggested_name}' saved successfully!")
                # Optionally clear the session data
                st.session_state["ai_screener_json"] = None
                st.rerun()

        st.write("---")
        
        # --- PART A: CREATE OR UPDATE A SCREEN ---
        st.write("### Create / Update a Stock Screen (Manual)")

        # Retrieve existing screens
        all_screens = db.get_stock_screens()
        screen_names = [sc["name"] for sc in all_screens]
        existing_screen_name = st.selectbox("Choose an Existing Screen to Edit (or leave blank)", [""] + screen_names)

        # If user selects an existing screen, populate fields
        if existing_screen_name:
            screen_data = next(sc for sc in all_screens if sc["name"] == existing_screen_name)
            default_name = screen_data["name"]
            default_criteria = json.dumps(screen_data["criteria"], indent=2)
            default_limit = screen_data["stock_limit"] if screen_data["stock_limit"] else 0
            screen_id = screen_data["id"]
        else:
            default_name = ""
            default_criteria = '{\n  "pe_ratio": {"max": 20},\n  "revenue_growth_yoy": {"min": 5}\n}'
            default_limit = 0
            screen_id = None

        col_create1, col_create2 = st.columns(2)
        with col_create1:
            name_input = st.text_input("Screen Name", value=default_name)
        with col_create2:
            stock_limit_input = st.number_input("Max Stocks to Return (0 = unlimited)", 
                                                min_value=0, value=default_limit, step=1)

        criteria_text = st.text_area("JSON Criteria", value=default_criteria, height=150)
        
        if st.button("Save Screen"):
            # Parse JSON criteria
            try:
                parsed_criteria = json.loads(criteria_text)
            except json.JSONDecodeError:
                st.error("Invalid JSON for criteria. Please fix and try again.")
                st.stop()

            # If editing an existing screen
            if screen_id:
                db.update_stock_screen(screen_id, name_input, parsed_criteria,
                                       stock_limit_input if stock_limit_input > 0 else None)
                st.success(f"Screen '{name_input}' updated!")
            else:
                # Creating a new screen
                db.add_stock_screen(name_input, parsed_criteria, 
                                    stock_limit_input if stock_limit_input > 0 else None)
                st.success(f"Screen '{name_input}' created!")
            st.rerun()

        # --- PART B: LINK SCREENS TO PORTFOLIOS ---
        st.write("---")
        st.write("### Link a Screen to a Portfolio")

        updated_screens = db.get_stock_screens()  # refresh
        if updated_screens:
            link_screen = st.selectbox("Select Screen to Link", [sc["name"] for sc in updated_screens])
            link_screen_data = next(sc for sc in updated_screens if sc["name"] == link_screen)

            # Choose portfolio
            if portfolios:
                link_portfolio_id = st.selectbox("Select Portfolio to Link", portfolio_ids,
                                                 format_func=lambda x: portfolio_dict[x])
                if st.button("Link Screen to Portfolio"):
                    db.link_screen_to_portfolio(link_portfolio_id, link_screen_data["id"])
                    st.success(f"Linked '{link_screen}' to {portfolio_dict[link_portfolio_id]}")
            else:
                st.info("No portfolios to link. Please create one first.")
        else:
            st.info("No stock screens found. Create one above.")

        # --- PART C: View and Manage Links ---
        st.write("---")
        st.write("### Manage Existing Screens & Portfolio Links")

        all_screens = db.get_stock_screens()
        if all_screens:
            for sc in all_screens:
                with st.expander(f"{sc['name']}"):
                    st.json(sc["criteria"])
                    st.write(f"Max Stocks to Return: {sc['stock_limit'] if sc['stock_limit'] else 'Unlimited'}")

                    # Which portfolios is this screen linked to?
                    db.cursor.execute('''
                        SELECT ps.portfolio_id
                        FROM portfolio_screens ps
                        WHERE ps.screen_id = ?
                    ''', (sc["id"],))
                    linked_port_ids = [row[0] for row in db.cursor.fetchall()]

                    if linked_port_ids:
                        st.write("Linked to:")
                        for pid in linked_port_ids:
                            st.write(f"- {portfolio_dict.get(pid, f'Portfolio ID {pid}')}")
                        # Optionally remove link:
                        remove_port = st.selectbox(f"Remove link from {sc['name']}", 
                                                   [pid for pid in linked_port_ids], 
                                                   format_func=lambda x: portfolio_dict[x] if x in portfolio_dict else str(x),
                                                   key=f"remove_link_{sc['id']}")
                        if st.button(f"Unlink from {remove_port}", key=f"remove_link_btn_{sc['id']}"):
                            db.unlink_screen_from_portfolio(remove_port, sc["id"])
                            st.warning(f"Unlinked from {portfolio_dict.get(remove_port, remove_port)}.")
                            st.rerun()
                    else:
                        st.write("No portfolios linked yet.")

                    # Option to delete this screen entirely
                    if st.button(f"Delete Screen '{sc['name']}'", key=f"delete_screen_{sc['id']}"):
                        db.delete_stock_screen(sc["id"])
                        st.warning(f"Deleted stock screen '{sc['name']}'.")
                        st.rerun()
        else:
            st.info("No stock screens found. Create one above.")

        # --- PART D: Apply a Screen & Add Results to Portfolio ---
        st.write("---")
        st.write("### Apply a Screen to See Matching Stocks")

        # 1) Use session_state to store the last-applied screen's data
        if "applied_screen" not in st.session_state:
            st.session_state["applied_screen"] = None  # will store screen name
        if "applied_results" not in st.session_state:
            st.session_state["applied_results"] = []
        if "applied_ignored" not in st.session_state:
            st.session_state["applied_ignored"] = []

        if updated_screens:
            chosen_screen_name = st.selectbox("Choose a Screen to Apply", [sc["name"] for sc in updated_screens])
            chosen_screen_data = next(sc for sc in updated_screens if sc["name"] == chosen_screen_name)

            # Pressing "Apply Screen" does the DB query & saves results in session
            if st.button("Apply Screen"):
                applied_result = db.apply_stock_screen(chosen_screen_data["id"])
                st.session_state["applied_screen"] = chosen_screen_name
                st.session_state["applied_results"] = applied_result.get("results", [])
                st.session_state["applied_ignored"] = applied_result.get("ignored_filters", [])

            # Only display results if the user has previously "applied" this screen
            if (
                st.session_state["applied_screen"] == chosen_screen_name 
                and st.session_state["applied_results"]
            ):
                results = st.session_state["applied_results"]
                ignored = st.session_state["applied_ignored"]

                if ignored:
                    st.warning(f"Ignored filter keys (not recognized in fundamentals): {', '.join(ignored)}")

                df_results = pd.DataFrame(results)
                st.write(f"Found {len(df_results)} matching stocks:")
                st.dataframe(df_results)

                # Option to add selected stocks to the selected portfolio
                if selected_portfolio_id is not None:
                    selected_stocks = st.multiselect(
                        "Select Stocks to Add to Portfolio",
                        df_results["ticker"].tolist()
                    )
                    if st.button("Add to Portfolio"):
                        if not selected_stocks:
                            st.warning("No stocks selected.")
                        else:
                            existing_port_stocks = {s[2] for s in db.get_stocks(selected_portfolio_id)}
                            added_count = 0

                            # We'll create a new list of results that excludes newly added stocks
                            updated_results = []

                            for row in results:
                                ticker = row["ticker"]
                                if ticker in selected_stocks and ticker not in existing_port_stocks:
                                    db.add_stock(selected_portfolio_id, ticker)
                                    added_count += 1
                                else:
                                    updated_results.append(row)

                            st.session_state["applied_results"] = updated_results
                            st.success(f"Added {added_count} new stocks to your portfolio.")

                            # Display updated portfolio
                            port_stocks = db.get_stocks(selected_portfolio_id)
                            st.write("**Updated Portfolio Stocks (No Trades):**")
                            df_port = pd.DataFrame(port_stocks, columns=["ID", "Portfolio ID", "Ticker"])
                            st.dataframe(df_port[["ID", "Ticker"]])
                else:
                    st.info("Select a portfolio in the sidebar to add stocks.")
            else:
                st.info("Press 'Apply Screen' to see matching stocks.")
        else:
            st.info("Create a screen first.")

    # -------------------------------------------------------------------------
    # Close DB connection at the end
    # -------------------------------------------------------------------------
    db.close_connection()

if __name__ == "__main__":
    main()
