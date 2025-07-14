import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import date

from chatgpt_api import generate_trading_strategy
from database import TradingDatabase  # Import the TradingDatabase class

# Initialize database connection
db = TradingDatabase()

# ====== Streamlit App Title & Layout ======
st.set_page_config(page_title="Trading Dashboard", layout="wide")
st.title("📊 AI-Powered Trading Dashboard")

# -----------------------------------------------------------------------------
# Helper: Load all portfolios + dictionary
# -----------------------------------------------------------------------------
def load_portfolios():
    pf = db.get_portfolios()
    pf_dict = {p[0]: f"{p[1]} (${p[2]:,.2f}) - {p[3]}" for p in pf}
    return pf, pf_dict

portfolios, portfolio_dict = load_portfolios()
portfolio_ids = list(portfolio_dict.keys())

# -----------------------------------------------------------------------------
# SIDEBAR: Select portfolio + quick summary
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Create TABS
# -----------------------------------------------------------------------------
tab_mgmt, tab_overview, tab_history, tab_compare, tab_strategy = st.tabs([
    "Portfolio Management",
    "Portfolio Overview",
    "Trade History & Filtering",
    "Compare Portfolios",
    "AI-Powered Trading Strategies",
])

# =============================================================================
# TAB 1: Portfolio Management
# =============================================================================
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

# =============================================================================
# TAB 2: Portfolio Overview
# =============================================================================
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

# =============================================================================
# TAB 3: Trade History & Filtering (Add & Remove Trades)
# =============================================================================
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

# =============================================================================
# TAB 4: Compare Portfolios
# =============================================================================
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

# =============================================================================
# TAB 5: AI-Powered Trading Strategies
# =============================================================================
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
                    updated_strategy_text = st.text_area("Modify Strategy JSON", value=str(strategy_parameters))
                    if st.button(f"Update {strategy_name}"):
                        db.update_strategy(strategy_id, updated_strategy_text)
                        st.success("Strategy updated successfully!")
        else:
            st.info("No strategies found for this portfolio.")

# -----------------------------------------------------------------------------
# Finally, close the database connection
# -----------------------------------------------------------------------------
db.close_connection()
