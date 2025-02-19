import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from chatgpt_api import generate_trading_strategy
from database import TradingDatabase  # Import the TradingDatabase class

# Initialize database connection
db = TradingDatabase()

# ====== Streamlit App Title & Layout ======
st.set_page_config(page_title="Trading Dashboard", layout="wide")
st.title("📊 AI-Powered Trading Dashboard")

# === Sidebar - Portfolio Selection ===
st.sidebar.header("Manage Portfolios")

# Load Portfolios
portfolios = db.get_portfolios()
portfolio_dict = {p[0]: f"{p[1]} (${p[2]:,.2f}) - {p[3]}" for p in portfolios}
portfolio_ids = list(portfolio_dict.keys())

if portfolios:
    selected_portfolio_id = st.sidebar.selectbox(
        "Select a Portfolio", 
        portfolio_ids, 
        format_func=lambda x: portfolio_dict[x]
    )
else:
    st.sidebar.warning("No portfolios found. Please create one.")

# === Sidebar - Create New Portfolio ===
st.sidebar.subheader("Create a New Portfolio")
new_name = st.sidebar.text_input("Portfolio Name")
new_capital = st.sidebar.number_input("Initial Capital", min_value=0.0, step=100.0)
new_mode = st.sidebar.selectbox("Execution Mode", ["paper", "live"])

if st.sidebar.button("Add Portfolio"):
    if new_name and new_capital > 0:
        print(f"🟢 Debug: Calling add_portfolio with Name: {new_name}, Capital: {new_capital}, Mode: {new_mode}")
        db.add_portfolio(new_name, new_capital, new_mode)
        st.sidebar.success(f"Portfolio '{new_name}' added!")
        st.rerun()

# === Sidebar - Delete Portfolio ===
if portfolios:
    if st.sidebar.button("Delete Selected Portfolio"):
        db.delete_portfolio(selected_portfolio_id)
        st.sidebar.warning("Portfolio deleted!")
        st.rerun()

# === Portfolio Overview & Performance ===
if portfolios:
    st.subheader(f"Portfolio: {portfolio_dict[selected_portfolio_id]}")
    portfolio_value = db.calculate_portfolio_value(selected_portfolio_id)
    initial_capital = next(p[2] for p in portfolios if p[0] == selected_portfolio_id)
    return_percentage = ((portfolio_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0

    # **Performance Metrics**
    trades = db.get_trades(selected_portfolio_id)
    if trades:
        df_trades = pd.DataFrame(trades, columns=[
            "ID", "Portfolio ID", "Stock", 
            "Type", "Quantity", "Price", 
            "Transaction Cost", "Timestamp"
        ])
        df_trades["Total Cost"] = df_trades["Quantity"] * df_trades["Price"] + df_trades["Transaction Cost"]
        df_trades["Timestamp"] = pd.to_datetime(df_trades["Timestamp"])
        df_trades = df_trades.sort_values("Timestamp")

        # Portfolio Performance Over Time
        df_trades["Cumulative Return"] = df_trades["Total Cost"].cumsum()

        # Sharpe Ratio Calculation (Assuming risk-free rate = 0)
        returns = df_trades["Cumulative Return"].pct_change().dropna()
        sharpe_ratio = np.mean(returns) / np.std(returns) if not returns.empty else 0

        # Drawdown Calculation
        cumulative_max = df_trades["Cumulative Return"].cummax()
        drawdown = df_trades["Cumulative Return"] - cumulative_max
        max_drawdown = drawdown.min()

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 Portfolio Value", value=f"${portfolio_value:,.2f}")
        st.metric(label="📈 Portfolio Return", value=f"{return_percentage:.2f}%")

    with col2:
        st.subheader("📊 Performance Metrics")
        st.write(f"Initial Capital: **${initial_capital:,.2f}**")
        st.write(f"Current Value: **${portfolio_value:,.2f}**")
        st.write(f"Total Return: **{return_percentage:.2f}%**")
        if trades:
            st.write(f"📉 Max Drawdown: **${max_drawdown:,.2f}**")
            st.write(f"📊 Sharpe Ratio: **{sharpe_ratio:.2f}**")

# === AI Strategy Generation ===
st.subheader("💡 AI-Powered Trading Strategies")

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

# === Assign and Save Strategy ===
if st.session_state["strategy"] is not None:
    st.subheader("Assign and Save Strategy")

    # Refresh the list of portfolios in case user created a new one
    portfolios_for_assign = db.get_portfolios()
    if portfolios_for_assign:
        selected_portfolio_id_for_strategy = st.selectbox(
            "Assign Strategy to Portfolio",
            [p[0] for p in portfolios_for_assign],
            format_func=lambda pid: next(
                (f"{p[1]} (${p[2]:,.2f}) - {p[3]}" for p in portfolios_for_assign if p[0] == pid),
                str(pid)
            )
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

# === View and Edit Existing Strategies ===
if portfolios:
    st.subheader("📌 Existing Strategies for Portfolio")
    strategies = db.get_portfolio_strategies(selected_portfolio_id)
    print(f"📌 Debug: Retrieved strategies for portfolio {selected_portfolio_id}: {strategies}")

    if strategies:
        for sdict in strategies:
            print(f"📝 Strategy Found: {sdict}")  # Debug output
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
        st.write("No strategies found for this portfolio.")

# === Clean Up Database ===
st.sidebar.subheader("Database Maintenance")
if st.sidebar.button("Clean Database (Remove Orphans)"):
    db.clean_database()
    st.sidebar.success("Database cleaned!")

# Close database connection
db.close_connection()
