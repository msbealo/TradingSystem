import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
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
    selected_portfolio_id = st.sidebar.selectbox("Select a Portfolio", portfolio_ids, format_func=lambda x: portfolio_dict[x])
else:
    st.sidebar.warning("No portfolios found. Please create one.")

# === Portfolio Overview & Performance ===
if portfolios:
    st.subheader(f"Portfolio: {portfolio_dict[selected_portfolio_id]}")
    portfolio_value = db.calculate_portfolio_value(selected_portfolio_id)
    initial_capital = next(p[2] for p in portfolios if p[0] == selected_portfolio_id)
    return_percentage = ((portfolio_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0

    # **Sharpe Ratio & Drawdown Calculation**
    trades = db.get_trades(selected_portfolio_id)
    if trades:
        df_trades = pd.DataFrame(trades, columns=["ID", "Portfolio ID", "Stock", "Type", "Quantity", "Price", "Transaction Cost", "Timestamp"])
        df_trades["Total Cost"] = df_trades["Quantity"] * df_trades["Price"] + df_trades["Transaction Cost"]
        df_trades["Timestamp"] = pd.to_datetime(df_trades["Timestamp"])
        df_trades = df_trades.sort_values("Timestamp")

        # Portfolio Performance Over Time
        df_trades["Cumulative Return"] = df_trades["Total Cost"].cumsum()

        # Calculate Sharpe Ratio (Assuming risk-free rate = 0 for simplicity)
        returns = df_trades["Cumulative Return"].pct_change().dropna()
        sharpe_ratio = np.mean(returns) / np.std(returns) if not returns.empty else 0

        # Calculate Drawdown
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

    # === Trade History with Date Filtering ===
    st.subheader("📊 Trade History & Filtering")

    if trades:
        # Add Date Filters
        start_date = st.date_input("Start Date", df_trades["Timestamp"].min().date())
        end_date = st.date_input("End Date", df_trades["Timestamp"].max().date())

        filtered_trades = df_trades[
            (df_trades["Timestamp"].dt.date >= start_date) & 
            (df_trades["Timestamp"].dt.date <= end_date)
        ]

        st.dataframe(filtered_trades.drop(columns=["Portfolio ID"]))

        # Export to CSV
        csv = filtered_trades.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Trades as CSV",
            data=csv,
            file_name=f"trade_history_{selected_portfolio_id}.csv",
            mime="text/csv"
        )

    # === Portfolio Comparison Chart ===
    st.subheader("📊 Compare Portfolio Performance")
    selected_portfolios = st.multiselect("Select Portfolios to Compare", portfolio_dict.keys(), format_func=lambda x: portfolio_dict[x])

    if selected_portfolios:
        portfolio_values = {p_id: db.calculate_portfolio_value(p_id) for p_id in selected_portfolios}
        df_comparison = pd.DataFrame(list(portfolio_values.items()), columns=["Portfolio ID", "Portfolio Value"])
        df_comparison["Portfolio Name"] = df_comparison["Portfolio ID"].apply(lambda x: portfolio_dict[x])

        fig, ax = plt.subplots()
        ax.bar(df_comparison["Portfolio Name"], df_comparison["Portfolio Value"], color="skyblue")
        ax.set_xlabel("Portfolios")
        ax.set_ylabel("Portfolio Value ($)")
        ax.set_title("Portfolio Value Comparison")
        st.pyplot(fig)

    # === Interactive Portfolio Value Over Time Chart ===
    if trades:
        st.subheader("📈 Portfolio Performance Over Time")
        fig2, ax2 = plt.subplots()
        ax2.plot(df_trades["Timestamp"], df_trades["Cumulative Return"], marker="o", linestyle="-", color="blue", label="Cumulative Return")
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Portfolio Value ($)")
        ax2.set_title("Portfolio Value Over Time")
        ax2.legend()
        st.pyplot(fig2)

# === Clean Up Database ===
st.sidebar.subheader("Database Maintenance")
if st.sidebar.button("Clean Database (Remove Orphans)"):
    db.clean_database()
    st.sidebar.success("Database cleaned!")

# Close database connection
db.close_connection()
