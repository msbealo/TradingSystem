import streamlit as st
from database import TradingDatabase
from data_fetcher import StockDataFetcher
from chatgpt_api import ChatGPTAPI
from Strategy_builder import build_strategy_class
from backtest_engine import BacktsestEngine
from ftse_fetcher import FTSETickerFetcher
import datetime
import json
import pandas as pd
import altair as alt
from dateutil.relativedelta import relativedelta

# ---------------------------------------
# Initialize shared objects and session
# ---------------------------------------
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")

# Session state: init once
if "selected_portfolio_id" not in st.session_state:
    st.session_state["selected_portfolio_id"] = None
if "date_range" not in st.session_state:
    st.session_state["date_range"] = ("2020-01-01", datetime.datetime.now().strftime("%Y-%m-%d"))

# Core objects
db = TradingDatabase()
fetcher = StockDataFetcher(db)
chat = ChatGPTAPI()
backtester = BacktsestEngine(db)

# ---------------------------------------
# Sidebar: Global Portfolio Selector
# ---------------------------------------
st.sidebar.title("💼 Portfolio Selector")
portfolios = db.get_portfolios()
portfolio_dict = {p[0]: f"{p[1]} (${p[2]:,.2f}) - {p[3]}" for p in portfolios}
portfolio_ids = list(portfolio_dict.keys())

if portfolio_ids:
    selected_id = st.sidebar.selectbox(
        "Select Portfolio",
        portfolio_ids,
        format_func=lambda x: portfolio_dict[x],
        key="selected_portfolio_id_widget"  # Use a different key for the widget
    )
    st.session_state["selected_portfolio_id"] = selected_id  # Then update your state variable
else:
    st.sidebar.warning("No portfolios yet.")

# Date Range
start_date, end_date = st.sidebar.date_input(
    "Backtest Date Range", value=(datetime.date(2020, 1, 1), datetime.date.today())
)
st.session_state["date_range"] = (str(start_date), str(end_date))

# ---------------------------------------
# TABS
# ---------------------------------------
tabs = st.tabs([
    "📁 Portfolios",
    "🧠 Strategies",
    "📈 Data",
    "🔎 Screener",
    "📊 Backtesting",
    "📜 History",
    "📊 Compare"
])

tab_portfolio, tab_strategy, tab_fundamentals, tab_screener, tab_backtest, tab_history, tab_compare = tabs

# ---------------------------------------
# TAB: Portfolio Manager (Skeleton)
# ---------------------------------------
with tab_portfolio:
    st.header("📁 Portfolio Manager")

    # --- Section: Create New Portfolio ---
    st.subheader("➕ Create a New Portfolio")
    with st.form("create_portfolio_form", clear_on_submit=True):
        new_name = st.text_input("Portfolio Name")
        new_capital = st.number_input("Starting Capital (£)", min_value=1000.0, step=500.0)
        new_mode = st.selectbox("Execution Mode", ["paper", "live"])
        create = st.form_submit_button("Create Portfolio")
        if create:
            db.add_portfolio(new_name, new_capital, new_mode)
            st.success(f"Portfolio '{new_name}' created.")
            st.rerun()

    # --- Section: Portfolio Actions ---
    if st.session_state["selected_portfolio_id"]:
        pid = st.session_state["selected_portfolio_id"]
        st.markdown("---")
        st.subheader(f"⚙️ Managing Portfolio: {portfolio_dict[pid]}")
        
        # Delete button
        if st.button("❌ Delete This Portfolio"):
            db.delete_portfolio(pid)
            st.session_state["selected_portfolio_id"] = None
            st.success("Portfolio deleted.")
            st.rerun()
      
        # --- Section: Stocks in Portfolio ---
        st.subheader("📈 Stocks in Portfolio")
        stocks = db.get_stocks(pid)
        if stocks:
            st.write([s[2] for s in stocks])
            remove_stock = st.text_input("Remove Stock Ticker (e.g., AAPL)")
            if st.button("Remove Stock"):
                db.remove_stock(pid, remove_stock.upper())
                st.success(f"Removed {remove_stock.upper()}")
                st.rerun()
        else:
            st.info("No stocks assigned.")
        
        add_stock = st.text_input("Add Stock Ticker (e.g., AAPL)")
        if st.button("Add Stock"):
            db.add_stock(pid, add_stock.upper())
            st.success(f"Added {add_stock.upper()}")
            st.rerun()

        # --- Section: Linked Strategies ---
        st.subheader("📑 Linked Strategies")
        linked_strats = db.get_strategies(pid)
        if linked_strats:
            for s in linked_strats:
                # Each expander displays one strategy's details.
                with st.expander(s['name']):
                    # Convert the strategy dictionary into a DataFrame of key/value pairs.
                    strategy_details = s.get("parameters", {})
                    st.json(strategy_details, expanded=False)
        else:
            st.info("No strategies linked to this portfolio.")

    else:
        st.warning("Select a portfolio in the sidebar to manage it.")


# ---------------------------------------
# TAB: Strategy Center (Skeleton)
# ---------------------------------------
with tab_strategy:
    st.header("🧠 Strategy Center")
    st.write("Create, edit, delete, and assign AI-generated strategies.")

    # --- CLEANUP BUTTON ---
    if st.button("🧹 Clean Orphaned Strategies and Screens"):
        db.clean_database()
        st.success("Database cleanup complete.")
        st.rerun()

    # --- CREATE NEW STRATEGY ---
    st.subheader("➕ Create New Strategy (via ChatGPT)")
    user_prompt = st.text_area("Describe your strategy (e.g., 'Buy when RSI < 30, sell when > 70')", height=100)
    
    # 1) Generate strategy
    if st.button("Generate Strategy"):
        with st.spinner("Generating strategy..."):
            new_strategy = chat.generate_trading_strategy(user_prompt)
        st.session_state["generated_strategy"] = new_strategy

    # 2) If we have a strategy in session, show a summaryv        
    if "generated_strategy" in st.session_state:
        strategy_json = st.session_state["generated_strategy"]
        if "strategy_name" in strategy_json:
            st.success(f"Generated Strategy: {strategy_json['strategy_name']}")
            st.json(strategy_json)  # Show the full JSON
       
            # 3) Only now show the form:
            with st.form("save_strategy_form"):
                st.write("➕DEBUG: Entered the form block")
                name = st.text_input("Confirm Strategy Name", value=strategy_json["strategy_name"])
                portfolios = db.get_portfolios()
                portfolio_dict = {p[0]: f"{p[1]} (${p[2]:,.0f})" for p in portfolios}
                selected_pids = st.multiselect("Assign to Portfolios", options=portfolio_dict.keys(), format_func=lambda x: portfolio_dict[x])
                
                save = st.form_submit_button("Save Strategy")
                st.write(f"➕DEBUG: save button value = {save}")
                if save:
                    print("➕DEBUG: name=", name, " selected_pids=", selected_pids)
                    print("➕DEBUG: Inside save button block!")
                    db.add_strategy(name, strategy_json, selected_pids)
                    st.success("➕Strategy saved.")
                    st.rerun()

        else:
            st.error("ChatGPT did not return a valid strategy.")

    else:
        st.info("No strategy yet. Generate one above.")

    # --- EXISTING STRATEGIES ---
    st.markdown("---")
    st.subheader("📄 View / Edit Existing Strategies")
    strategies = db.get_strategies()
    strategy_dict = {s["id"]: s["name"] for s in strategies}

    if not strategy_dict:
        st.info("No strategies available.")
    else:
        selected_id = st.selectbox("Select a strategy", options=list(strategy_dict.keys()), format_func=lambda x: strategy_dict[x])
        selected = next(s for s in strategies if s["id"] == selected_id)

        st.markdown(f"### 🧠 {selected['name']} (ID {selected_id})")

        # --- Show currently linked portfolios ---
        linked_portfolios = [
            (p[0], p[1])
            for p in db.get_portfolios()
            if selected_id in [s['id'] for s in db.get_strategies(p[0])]
        ]

        st.markdown("#### 📦 Currently Assigned To:")
        if linked_portfolios:
            for pid, pname in linked_portfolios:
                st.markdown(f"- **{pname}** (ID: {pid})")
        else:
            st.markdown("_Not linked to any portfolios._")

        # --- Editable JSON ---
        editable_json = st.text_area("Edit Strategy JSON", value=json.dumps(selected["parameters"], indent=2), height=300)
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("💾 Save Changes"):
                try:
                    parsed = json.loads(editable_json)
                    db.update_strategy(selected_id, parsed)
                    st.success("Strategy updated.")
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Invalid JSON.")

        with col2:
            if st.button("🗑️ Delete Strategy"):
                db.delete_strategy(selected_id)
                st.success("Strategy deleted.")
                st.rerun()

        # --- Portfolio Assignment ---
        st.markdown("#### 📦 Assign to Portfolios")
        all_portfolios = db.get_portfolios()
        portfolio_dict = {p[0]: f"{p[1]} (${p[2]:,.0f})" for p in all_portfolios}
        # Get currently assigned portfolios
        currently_linked = [p[0] for p in all_portfolios if selected_id in [s['id'] for s in db.get_strategies(p[0])]]

        selected_pids = st.multiselect("Linked Portfolios", options=portfolio_dict.keys(), default=currently_linked, format_func=lambda x: portfolio_dict[x])
        if st.button("Update Portfolio Links"):
            db.assign_strategy_to_portfolios(selected_id, selected_pids)
            st.success("Portfolio links updated.")
            st.rerun()

# ---------------------------------------
# TAB: Fundamentals & Prices (Skeleton)
# ---------------------------------------
with tab_fundamentals:
    st.header("📈 Fundamentals & Price Data")
    # Create sub-tabs for Ticker Data, Fundamentals, and Price Data
    sub_tabs = st.tabs(["Ticker Data", "Fundamentals", "Price Data"])

    # --- Sub-tab 1: Ticker Data ---
    with sub_tabs[0]:
        st.subheader("Scrape & Store FTSE Tickers")
        fetcher_ftse = FTSETickerFetcher()
        
        if st.button("Scrape FTSE Tickers"):
            with st.spinner("Scraping..."):
                tickers_dict = fetcher_ftse.get_all_ftse_index_tickers()
                st.session_state["all_tickers_dict"] = tickers_dict
            st.success("Scraped FTSE Tickers Successfully!")
            for index_name, tickers_list in tickers_dict.items():
                st.write(f"**{index_name}**: {len(tickers_list)} tickers")
                st.write(tickers_list)

        if st.button("Store Tickers in DB"):
            tickers_dict = st.session_state.get("all_tickers_dict", {})
            if not tickers_dict:
                st.warning("No tickers found in session. Please scrape first.")
            else:
                total_count = 0
                for index_name, tickers_list in tickers_dict.items():
                    for ticker in tickers_list:
                        db.add_master_stock(ticker)
                        total_count += 1
                st.success(f"Stored {total_count} tickers in DB.")

    # --- Sub-tab 2: Fundamentals ---
    with sub_tabs[1]:
        st.subheader("Fetch & View Fundamentals")

        force_refresh = st.checkbox("Force Update Fundamentals (Ignore 7-day rule)?", value=False)
        st.write("Click the button below to download fundamentals for all tickers in the database.")
        if st.button("Fetch Fundamentals for All Tickers in DB"):
            db_tickers = db.get_master_stock_tickers()  # Assumes this helper method exists
            if not db_tickers:
                st.warning("No tickers in DB. Please store tickers first.")
            else:
                progress_bar = st.progress(0)
                total = len(db_tickers)
                for i, ticker in enumerate(db_tickers, start=1):
                    info = fetcher.fetch_fundamental_data(ticker, force_refresh=force_refresh)
                    if i == 1:  # Only show the raw JSON for the first ticker
                        st.markdown(f"**Example output for {ticker}:**")
                        st.json(info)
                    progress_bar.progress(int((i / total) * 100))
                st.success(f"Fetched fundamentals for {total} tickers.")

        st.write("---")
        st.subheader("View Fundamentals for Selected Tickers")
        # Allow selection of multiple tickers.
        db_tickers_for_view = db.get_master_stock_tickers()
        selected_tickers = st.multiselect("Choose tickers to view fundamentals:", db_tickers_for_view)

        if selected_tickers:
            # Full list of fundamental keys in the updated fundamentals table:
            fundamental_keys = [
                "id", "ticker", "market_cap", "pe_ratio", "eps", "dividend_yield", "debt_to_equity", "last_updated",
                "forward_pe", "price_to_book", "price_to_sales", "enterprise_to_ebitda", "price_to_fcf",
                "net_profit_margin", "return_on_equity", "return_on_assets", "return_on_invested_capital",
                "eps_growth", "revenue_growth_yoy", "earnings_growth_yoy", "revenue_growth_3y", "eps_growth_3y",
                "dividend_payout_ratio", "dividend_growth_5y", "current_ratio", "quick_ratio", "interest_coverage",
                "free_float", "insider_ownership", "institutional_ownership", "beta", "price_change_52w",
                "max_age", "price_hint", "previous_close", "open_price", "day_low", "day_high",
                "regular_market_previous_close", "regular_market_open", "regular_market_day_low", "regular_market_day_high",
                "regular_market_volume", "average_volume", "average_volume_10days", "average_daily_volume_10day",
                "bid", "ask", "bid_size", "ask_size", "fifty_two_week_low", "fifty_two_week_high", "fifty_day_average",
                "two_hundred_day_average", "trailing_annual_dividend_rate", "trailing_annual_dividend_yield",
                "currency", "tradeable", "quote_type", "current_price", "target_high_price", "target_low_price",
                "target_mean_price", "target_median_price", "recommendation_key", "number_of_analyst_opinions",
                "financial_currency", "symbol", "language", "region", "type_disp", "quote_source_name", "triggerable",
                "custom_price_alert_confidence", "market_state", "long_name", "regular_market_change_percent",
                "short_name", "regular_market_time", "exchange", "message_board_id", "exchange_timezone_name",
                "exchange_timezone_short_name", "gmt_offset_milliseconds", "market", "esg_populated", "corporate_actions",
                "has_pre_post_market_data", "first_trade_date_milliseconds", "regular_market_change",
                "regular_market_day_range", "full_exchange_name", "average_daily_volume_3month",
                "fifty_two_week_low_change", "fifty_two_week_low_change_percent", "fifty_two_week_range",
                "fifty_two_week_high_change", "fifty_two_week_high_change_percent", "fifty_two_week_change_percent",
                "earnings_timestamp_start", "earnings_timestamp_end", "is_earnings_date_estimate",
                "eps_trailing_twelve_months", "eps_forward", "eps_current_year", "price_eps_current_year",
                "shares_outstanding", "book_value", "fifty_day_average_change", "fifty_day_average_change_percent",
                "two_hundred_day_average_change", "two_hundred_day_average_change_percent", "source_interval",
                "exchange_data_delayed_by", "crypto_tradeable", "trailing_peg_ratio", "industry", "sector" 
            ]
            
            # Create a dictionary to store fundamentals for each selected ticker.
            fundamentals_by_ticker = {}
            for ticker in selected_tickers:
                data = db.get_fundamentals(ticker)
                if data:
                    # Convert tuple to dictionary using the full list of keys.
                    fundamentals_by_ticker[ticker] = dict(zip(fundamental_keys, data))
                else:
                    fundamentals_by_ticker[ticker] = {key: None for key in fundamental_keys}
            
            # Create a DataFrame where each column is a ticker.
            df_fundamentals = pd.DataFrame(fundamentals_by_ticker)
            
            # Optionally remove the redundant 'ticker' row if present.
            if "ticker" in df_fundamentals.index:
                df_fundamentals = df_fundamentals.drop("ticker")
            
             # 1) Build a row for "Company Name" from each ticker’s "long_name"
            company_names = {
                ticker: fundamentals_by_ticker[ticker].get("long_name", ticker)
                for ticker in selected_tickers
            }

             # Wrap this in a 1-row DataFrame
            df_company_names = pd.DataFrame(company_names, index=["Company Name"])
            
            # 2) Concatenate that row above the main fundamentals data
            print(f"DEBUG: Combining data df_company_names={df_company_names}")
            df_combined = pd.concat([df_company_names, df_fundamentals])
            print(f"DEBUG: After combining data df_company_names={df_company_names}")

            # Force every value in df_combined to string
            df_combined = df_combined.fillna("").astype(str)

            st.dataframe(df_combined)
        else:
            st.info("Please select one or more tickers to view their fundamentals.")
            
    # --- Sub-tab 3: Price Data ---
    # --- Sub-tab 3: Price Data ---
    with sub_tabs[2]:
        st.subheader("Fetch & View Price Data for a Ticker")

        # 1) Let user choose a ticker (either from your DB or by typing it manually).
        db_tickers_for_price = db.get_master_stock_tickers()
        chosen_ticker_price = ""
        if db_tickers_for_price:
            chosen_ticker_price = st.selectbox(
                "Choose a ticker:", [""] + db_tickers_for_price
            )

        typed_ticker = st.text_input("Or type a ticker manually (e.g., 'VOD.L'):")
        final_ticker = typed_ticker.strip() if typed_ticker.strip() else chosen_ticker_price

        # 2) Show the chosen ticker and fetch its 'long_name' from fundamentals
        start_date_input = st.date_input(
            "Select Start Date for Price Data", 
            value=datetime.date(2020, 1, 1)
        )
        start_date_str = start_date_input.strftime("%Y-%m-%d")

        st.write(f"**Current Ticker Selection:** {final_ticker if final_ticker else '(None Selected)'}")
        st.write(f"**Download Start Date:** {start_date_str}")

        # >>>> NEW CODE: retrieve the 'long_name' from fundamentals <<<<
        if final_ticker:
            long_name_val = db.get_fundamental_value(final_ticker, "long_name")
            print(f"DEBUG: long_name_val={long_name_val}")
            if long_name_val:
                print(f"DEBUG: write name to scrren. long_name_val={long_name_val}")
                st.write(f"**Company Name:** {long_name_val}")
            else:
                st.write("**Company Name:** (No 'long_name' found)")

        # 3) Buttons for fetching / viewing price data
        col_fetch, col_view = st.columns(2)
        with col_fetch:
            if st.button("Fetch Price Data"):
                if not final_ticker:
                    st.warning("No ticker selected. Please choose or type a ticker.")
                else:
                    fetcher.fetch_price_data(final_ticker, start_date=start_date_str)
                    st.success(f"Fetched price data for {final_ticker} starting from {start_date_str}.")

        with col_view:
            if "view_price_data" not in st.session_state:
                st.session_state["view_price_data"] = False
            if st.button("View Price Data"):
                st.session_state["view_price_data"] = True

        # 4) Timeframe selection for the chart
        timeframe = st.radio(
            "Select Time Frame",
            options=["5D", "1M", "3M", "6M", "YTD", "1Y", "5Y", "ALL"],
            horizontal=True,
            key="timeframe"
        )

        # 5) If user wants to view, load from DB and filter/plot
        if st.session_state["view_price_data"]:
            if not final_ticker:
                st.warning("No ticker selected. Please choose or type a ticker.")
            else:
                price_rows = db.get_price_data(final_ticker)
                if not price_rows:
                    st.info("No price data found in DB. Please fetch price data first.")
                else:
                    # Create a DataFrame from stored rows
                    cols = ["date", "open_price", "high_price", "low_price", "close_price", "adjusted_close", "volume"]
                    df_prices = pd.DataFrame(price_rows, columns=cols)
                    df_prices["date"] = pd.to_datetime(df_prices["date"])
                    df_prices.sort_values("date", inplace=True)
                    df_reset = df_prices.reset_index(drop=True)

                    # Create a "bar_end" for volume bars
                    df_reset["bar_end"] = df_reset["date"] + pd.Timedelta(days=1)

                    # Filter by timeframe
                    today = datetime.date.today()
                    if timeframe == "5D":
                        filter_start = pd.Timestamp(today - datetime.timedelta(days=5))
                    elif timeframe == "1M":
                        filter_start = pd.Timestamp(today - relativedelta(months=1))
                    elif timeframe == "3M":
                        filter_start = pd.Timestamp(today - relativedelta(months=3))
                    elif timeframe == "6M":
                        filter_start = pd.Timestamp(today - relativedelta(months=6))
                    elif timeframe == "YTD":
                        filter_start = pd.Timestamp(datetime.date(today.year, 1, 1))
                    elif timeframe == "1Y":
                        filter_start = pd.Timestamp(today - relativedelta(years=1))
                    elif timeframe == "5Y":
                        filter_start = pd.Timestamp(today - relativedelta(years=5))
                    else:  # "ALL"
                        filter_start = None

                    if filter_start is not None:
                        df_filtered = df_reset[df_reset["date"] >= filter_start]
                    else:
                        df_filtered = df_reset.copy()

                    # Build the charts
                    price_line = alt.Chart(df_filtered).mark_line().encode(
                        x=alt.X('date:T', title='Date'),
                        y=alt.Y('close_price:Q', title='Closing Price')
                    )

                    volume_bars = alt.Chart(df_filtered).mark_bar(opacity=0.3).encode(
                        x=alt.X('date:T', title='Date'),
                        x2='bar_end:T',
                        y=alt.Y('volume:Q', title='Volume', scale=alt.Scale(zero=True))
                    )

                    layered_chart = alt.layer(volume_bars, price_line).resolve_scale(
                        y='independent'
                    ).properties(width=700, height=400)

                    st.altair_chart(layered_chart, use_container_width=True)

# ---------------------------------------
# TAB: Screener Center (Skeleton)
# ---------------------------------------
with tab_screener:
    st.header("🔎 Screener Center")
    
    # Create sub-tabs for the two workflows
    screener_subtabs = st.tabs(["AI-Generated Screener", "Manual & Manage Screens"])
    
    # ===============================================================
    # Sub-tab 1: AI-Generated Screener
    # ===============================================================
    with screener_subtabs[0]:
        st.subheader("AI-Generated Screener")
        user_screener_prompt = st.text_area(
            "Enter screening criteria:",
            placeholder="Example: 'Find quality stocks with high ROE and low debt-to-equity.'",
            key="ai_screener_prompt_key"
        )
        if st.button("Generate Screener via ChatGPT", key="ai_generate"):
            if user_screener_prompt.strip():
                ai_response = chat.generate_stock_screener(user_screener_prompt.strip())
                if "error" in ai_response:
                    st.error(f"ChatGPT Error: {ai_response['error']}")
                else:
                    st.session_state["ai_screener_json"] = ai_response
                    st.success("AI-generated screener JSON:")
                    st.json(ai_response)
            else:
                st.warning("Please enter your screening criteria in natural language.")
        
        # If we have an AI screener output, let the user edit and save it
        if st.session_state.get("ai_screener_json") and "criteria" in st.session_state["ai_screener_json"]:
            ai_screener = st.session_state["ai_screener_json"]
            # Use the new fields: criteria_name and description
            default_name = ai_screener.get("criteria_name", "AI Screener")
            default_description = ai_screener.get("description", "")
            st.markdown("#### Save AI-Generated Screener")
            new_name = st.text_input("Screen Name", value=default_name, key="ai_screen_save_name")
            new_description = st.text_input("Description", value=default_description, key="ai_screen_description")
            if st.button("Save AI Screener", key="save_ai_screen"):
                # Save using the new screen name (and optionally, the description if you wish to extend your DB schema)
                screener_criteria = ai_screener["criteria"]
                db.add_stock_screen(new_name, screener_criteria, stock_limit=None)
                st.success(f"Screener '{new_name}' saved successfully!")
                st.session_state["ai_screener_json"] = None
                st.rerun()
    
    # ===============================================================
    # Sub-tab 2: Manual & Manage Screens
    # ===============================================================
    with screener_subtabs[1]:
        st.subheader("Manual & Manage Screens")
        # Single drop-down to either select an existing screen or create a new one
        all_screens = db.get_stock_screens()
        screen_options = [""] + [sc["name"] for sc in all_screens]
        selected_screen = st.selectbox("Select an existing screen to edit (or leave blank to create new)", screen_options, key="manual_screen_select")
        
        # Load details for selected screen; otherwise, set defaults for a new one
        if selected_screen:
            screen_data = next(sc for sc in all_screens if sc["name"] == selected_screen)
            default_name = screen_data["name"]
            default_criteria = json.dumps(screen_data["criteria"], indent=2)
            default_limit = screen_data["stock_limit"] if screen_data["stock_limit"] else 0
            screen_id = screen_data["id"]
        else:
            default_name = ""
            default_criteria = '{\n  "pe_ratio": {"max": 25},\n  "return_on_equity": {"min": 15},\n  "debt_to_equity": {"max": 0.5},\n  "profit_margin": {"min": 10}\n}'
            default_limit = 0
            screen_id = None
        
        st.text_input("Screen Name", value=default_name, key="manual_screen_name")
        criteria_text = st.text_area("JSON Criteria", value=default_criteria, height=150, key="manual_criteria")
        stock_limit_input = st.number_input("Max Stocks to Return (0 = unlimited)", min_value=0, value=default_limit, step=1, key="manual_stock_limit")
        
        st.markdown("#### Assign Screen to Portfolios")
        # Get portfolios and map their details
        portfolios = db.get_portfolios()
        portfolio_dict = {p[0]: f"{p[1]} (${p[2]:,.2f}) - {p[3]}" for p in portfolios}
        portfolio_ids = list(portfolio_dict.keys())
        # For an existing screen, get the currently linked portfolios
        linked_portfolios = []
        if screen_id:
            db.cursor.execute("SELECT portfolio_id FROM portfolio_screens WHERE screen_id = ?", (screen_id,))
            linked_portfolios = [row[0] for row in db.cursor.fetchall()]
        selected_linked = st.multiselect("Linked Portfolios", options=portfolio_ids, default=linked_portfolios,
                                         format_func=lambda x: portfolio_dict.get(x, str(x)),
                                         key="manual_linked_portfolios")
        
        col_update, col_delete = st.columns(2)
        with col_update:
            if st.button("Save / Update Screen", key="update_manual_screen"):
                try:
                    parsed_criteria = json.loads(criteria_text)
                except json.JSONDecodeError:
                    st.error("Invalid JSON for criteria. Please fix and try again.")
                    st.stop()
                # Use the edited screen name from the input widget
                updated_name = st.session_state["manual_screen_name"]
                if screen_id:
                    db.update_stock_screen(screen_id, updated_name, parsed_criteria, stock_limit_input if stock_limit_input > 0 else None)
                    st.success(f"Screen '{updated_name}' updated!")
                else:
                    db.add_stock_screen(updated_name, parsed_criteria, stock_limit_input if stock_limit_input > 0 else None)
                    st.success(f"Screen '{updated_name}' created!")
                # Update portfolio links: first clear then re-add
                if screen_id:
                    db.cursor.execute("DELETE FROM portfolio_screens WHERE screen_id = ?", (screen_id,))
                    for pid in selected_linked:
                        db.link_screen_to_portfolio(pid, screen_id)
                    db.conn.commit()
                else:
                    # For new screen, fetch its id (assumes new screen is the last one in the list)
                    new_screen = db.get_stock_screens()[-1]
                    for pid in selected_linked:
                        db.link_screen_to_portfolio(pid, new_screen["id"])
                st.rerun()
        with col_delete:
            if screen_id and st.button(f"Delete Screen '{selected_screen}'", key="delete_manual_screen"):
                db.delete_stock_screen(screen_id)
                st.success(f"Deleted screen '{selected_screen}'.")
                st.rerun()
        
        st.markdown("---")
        st.subheader("Apply Screen & Add Stocks to Portfolios")
        # Use the same screen selection above for applying the screen.
        apply_screen = selected_screen if selected_screen else st.text_input("Enter the name of the screen to apply", key="apply_screen_input")
        if apply_screen:
            # Find the screen by name
            screen_to_apply = None
            for sc in db.get_stock_screens():
                if sc["name"] == apply_screen:
                    screen_to_apply = sc
                    break
            if screen_to_apply:
                if st.button("Apply Screen", key="apply_screen_btn"):
                    applied_result = db.apply_stock_screen(screen_to_apply["id"])
                    st.session_state["applied_screen"] = apply_screen
                    st.session_state["applied_results"] = applied_result.get("results", [])
                    st.session_state["applied_ignored"] = applied_result.get("ignored_filters", [])
                if st.session_state.get("applied_screen") == apply_screen and st.session_state.get("applied_results"):
                    results = st.session_state["applied_results"]
                    ignored = st.session_state["applied_ignored"]
                    if ignored:
                        st.warning(f"Ignored filter keys: {', '.join(ignored)}")
                    df_results = pd.DataFrame(results)
                    st.write(f"Found {len(df_results)} matching stocks:")
                    st.dataframe(df_results)
                    
                    # Allow selection of which linked portfolio(s) to add the stocks to
                    add_to_portfolios = st.multiselect("Select portfolios to add stocks to", options=selected_linked,
                                                         format_func=lambda x: portfolio_dict.get(x, str(x)),
                                                         key="apply_screen_add_portfolios")
                    selected_stocks = st.multiselect("Select stocks to add", df_results["ticker"].tolist(), key="apply_screen_select_stocks")
                    if st.button("Add Selected Stocks to Portfolio(s)", key="add_stocks_apply"):
                        if not selected_stocks:
                            st.warning("No stocks selected.")
                        elif not add_to_portfolios:
                            st.warning("No portfolio selected.")
                        else:
                            added_count_total = 0
                            for pid in add_to_portfolios:
                                existing_port_stocks = {s[2] for s in db.get_stocks(pid)}
                                added_count = 0
                                updated_results = []
                                for row in results:
                                    ticker = row["ticker"]
                                    if ticker in selected_stocks and ticker not in existing_port_stocks:
                                        db.add_stock(pid, ticker)
                                        added_count += 1
                                    else:
                                        updated_results.append(row)
                                added_count_total += added_count
                            st.session_state["applied_results"] = updated_results
                            st.success(f"Added {added_count_total} new stocks to the selected portfolio(s).")
                            # Optionally, show updated stocks for each portfolio
                            for pid in add_to_portfolios:
                                port_stocks = db.get_stocks(pid)
                                st.write(f"**Updated Portfolio Stocks for {portfolio_dict.get(pid, pid)}:**")
                                df_port = pd.DataFrame(port_stocks, columns=["ID", "Portfolio ID", "Ticker"])
                                st.dataframe(df_port[["ID", "Ticker"]])
            else:
                st.info("Screen not found. Please ensure the screen exists.")

# ---------------------------------------
# TAB: Backtesting Dashboard
# ---------------------------------------
def create_combined_csv(price_df: pd.DataFrame, trades_df: pd.DataFrame) -> str:
    """
    Example helper to merge or concatenate price & trade data,
    returning CSV text that can be downloaded.
    Modify this function as needed to organize your columns.
    """
    if price_df.empty and trades_df.empty:
        return ""

    # For demonstration, let’s do a left join on 'date' if trades_df also has that column.
    # If your trades_df uses different column names, adapt accordingly.
    if not trades_df.empty and 'date' in trades_df.columns:
        combined_df = pd.merge(price_df, trades_df, on='date', how='left')
    else:
        # If no common column, you could just append or do some other logic
        combined_df = pd.concat([price_df, trades_df], axis=1)

    return combined_df.to_csv(index=False)

with tab_backtest:
    st.header("📊 Backtesting Dashboard")

    st.write("""
    Use this tab to run and view backtests of the strategies assigned to your currently selected portfolio.
    """)
    
    # Safety check: ensure a portfolio is actually selected
    if not st.session_state["selected_portfolio_id"]:
        st.warning("Please select a portfolio in the sidebar to run a backtest.")
    else:
        pid = st.session_state["selected_portfolio_id"]

        # Let the user choose which strategies to backtest
        all_strategies = db.get_strategies(pid)  # Strategies assigned to this portfolio
        if not all_strategies:
            st.info("No strategies linked to this portfolio. Add or link a strategy first.")
        else:
            # The user can pick either "all" or a subset
            strategy_ids = [s["id"] for s in all_strategies]
            strategy_names_map = {s["id"]: s["name"] for s in all_strategies}
            selected_strat_ids = st.multiselect(
                "Select strategies to backtest",
                options=strategy_ids,
                format_func=lambda x: strategy_names_map[x],
                default=strategy_ids  # by default, select all
            )

            # Let the user pick date range, or use what's in st.session_state
            start_date, end_date = st.session_state["date_range"]

            if st.button("Run Backtest Now"):
                # 1) Build a dictionary for the portfolio
                portfolio_info = db.get_portfolios()
                portfolio_row = next((p for p in portfolio_info if p[0] == pid), None)
                if not portfolio_row:
                    st.error("Could not find the selected portfolio in the database.")
                else:
                    # portfolio_row is (id, name, capital, execution_mode)
                    portfolio_capital = portfolio_row[2]
                    portfolio = {"capital": portfolio_capital}

                    # 2) Gather strategies in the format:
                    #    [{
                    #        "name": <str>,
                    #        "class": <strategy_class>,
                    #        "stocks": [tickers...]
                    #     }, ... ]
                    chosen_strategies = []
                    for s in all_strategies:
                        if s["id"] not in selected_strat_ids:
                            continue
                        # Build a Backtrader-ready strategy class from the JSON
                        strat_class = build_strategy_class(s["parameters"])

                        # Collect all stocks for this portfolio
                        p_stocks = db.get_stocks(pid)  # list of tuples
                        assigned_tickers = [row[2] for row in p_stocks]  # each row is (id, pid, ticker)

                        chosen_strategies.append({
                            "name": s["name"],
                            "class": strat_class,
                            "stocks": assigned_tickers
                        })

                    # 3) Run the backtest via your backtest engine
                    try:
                        results_dict = backtester.run_portfolio_backtest(
                            portfolio=portfolio,
                            strategies=chosen_strategies,
                            start_date=start_date,
                            end_date=end_date
                        )

                        # 4) Display aggregated performance results
                        st.subheader("Portfolio-Level Performance")
                        st.write(f"**Cumulative Return:** {results_dict['cumulative_return']:.2f}%")
                        st.write(f"**Sharpe Ratio:** {results_dict['sharpe_ratio']:.2f}")
                        st.write(f"**Max Drawdown:** {results_dict['max_drawdown']:.2f}%")
                        st.write(f"**Win Rate:** {results_dict['win_rate']:.2f}%")
                        st.write(f"**Total Trades:** {results_dict['total_trades']}")
                        st.write(f"**Winning Trades:** {results_dict['winning_trades']}")
                        st.write(f"**Losing Trades:** {results_dict['losing_trades']}")

                        # 5) Access per-strategy/per-stock details
                        detailed_results = results_dict.get("detailed_results", [])
                        for detail in detailed_results:
                            strategy_name = detail["strategy"]
                            stock = detail["stock"]
                            st.markdown("---")
                            with st.expander(f"Strategy: {strategy_name} / Stock: {stock}"):
                                # 5a) Display Chart
                                fig = detail.get("chart_fig")
                                if fig:
                                    st.pyplot(fig)

                                # 5b) Display Trades Table
                                trades_df = detail.get("trades_df")
                                if trades_df is not None and not trades_df.empty:
                                    st.write("**Trade History**")
                                    st.dataframe(trades_df)

                                # 5c) Display Price Data
                                price_df = detail.get("price_df")
                                if price_df is not None and not price_df.empty:
                                    st.write("**Price Data**")
                                    st.dataframe(price_df)

                                # 5d) Display Indicator Log (Daily)
                                #     If you modified your strategy to store a daily log in e.g. `indicator_log_df`:
                                log_df = detail.get("indicator_log_df")  # or whatever key you used
                                if log_df is not None and not log_df.empty:
                                    st.write("**Daily Indicator Log**")
                                    st.dataframe(log_df.head(50))  # show first 50 rows

                                    # Download button for daily log
                                    log_csv_data = log_df.to_csv(index=False)
                                    st.download_button(
                                        label="Download Daily Log CSV",
                                        data=log_csv_data.encode("utf-8"),
                                        file_name=f"{strategy_name}_{stock}_daily_log.csv",
                                        mime="text/csv"
                                    )

                                # 5e) Download Combined CSV (price + trades, if desired)
                                combined_csv = create_combined_csv(price_df, trades_df)
                                if combined_csv:
                                    st.download_button(
                                        label="Download CSV (Price + Trades)",
                                        data=combined_csv.encode("utf-8"),
                                        file_name=f"{strategy_name}_{stock}_backtest.csv",
                                        mime="text/csv"
                                    )
                                    
                    except Exception as e:
                        st.error(f"Backtest failed: {str(e)}")

# ---------------------------------------
# TAB: Trade History (Skeleton)
# ---------------------------------------
with tab_history:
    st.header("📜 Trade History")
    st.write("✅ View, filter, and export historical trades.")


# ---------------------------------------
# TAB: Portfolio Comparison (Skeleton)
# ---------------------------------------
with tab_compare:
    st.header("📊 Compare Portfolios")
    st.write("✅ Visual comparison of portfolio performance.")

# ---------------------------------------
# Final Cleanup
# ---------------------------------------
db.close_connection()
