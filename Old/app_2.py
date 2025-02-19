import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 Portfolio Value", value=f"${portfolio_value:,.2f}")
        st.metric(label="📈 Portfolio Return", value=f"{return_percentage:.2f}%")

    with col2:
        st.subheader("📊 Portfolio Performance Metrics")
        st.write(f"Initial Capital: **${initial_capital:,.2f}**")
        st.write(f"Current Value: **${portfolio_value:,.2f}**")
        st.write(f"Total Return: **{return_percentage:.2f}%**")

    # === Export Trade History as CSV ===
    trades = db.get_trades(selected_portfolio_id)
    if trades:
        df_trades = pd.DataFrame(trades, columns=["ID", "Portfolio ID", "Stock", "Type", "Quantity", "Price", "Transaction Cost", "Timestamp"])
        df_trades["Total Cost"] = df_trades["Quantity"] * df_trades["Price"] + df_trades["Transaction Cost"]
        df_trades["Timestamp"] = pd.to_datetime(df_trades["Timestamp"])
        csv = df_trades.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download Trade History as CSV",
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

# === Clean Up Database ===
st.sidebar.subheader("Database Maintenance")
if st.sidebar.button("Clean Database (Remove Orphans)"):
    db.clean_database()
    st.sidebar.success("Database cleaned!")

# Close database connection
db.close_connection()
