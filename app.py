import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from database import TradingDatabase  # Import the TradingDatabase class

# Initialize database connection
db = TradingDatabase()

# ====== Streamlit App Title ======
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

# === Sidebar - Create New Portfolio ===
st.sidebar.subheader("Create a New Portfolio")
new_name = st.sidebar.text_input("Portfolio Name")
new_capital = st.sidebar.number_input("Initial Capital", min_value=0.0, step=100.0)
new_mode = st.sidebar.selectbox("Execution Mode", ["paper", "live"])
if st.sidebar.button("Add Portfolio"):
    if new_name and new_capital > 0:
        db.add_portfolio(new_name, new_capital, new_mode)
        st.sidebar.success(f"Portfolio '{new_name}' added!")
        st.rerun()

# === Sidebar - Delete Portfolio ===
if portfolios:
    if st.sidebar.button("Delete Selected Portfolio"):
        db.delete_portfolio(selected_portfolio_id)
        st.sidebar.warning("Portfolio deleted!")
        st.rerun()

# === Portfolio Details ===
if portfolios:
    st.subheader(f"Portfolio: {portfolio_dict[selected_portfolio_id]}")
    portfolio_value = db.calculate_portfolio_value(selected_portfolio_id)
    st.metric(label="💰 Portfolio Value", value=f"${portfolio_value:,.2f}")

    # === Show Stocks in Portfolio ===
    stocks = db.get_stocks(selected_portfolio_id)
    st.subheader("📈 Stocks in Portfolio")
    if stocks:
        df_stocks = pd.DataFrame(stocks, columns=["ID", "Portfolio ID", "Stock Ticker"])
        st.table(df_stocks.drop(columns=["Portfolio ID"]))
    else:
        st.info("No stocks in this portfolio.")

    # === Show Trades ===
    trades = db.get_trades(selected_portfolio_id)
    st.subheader("📊 Trade History")
    if trades:
        df_trades = pd.DataFrame(trades, columns=["ID", "Portfolio ID", "Stock", "Type", "Quantity", "Price", "Transaction Cost", "Timestamp"])
        st.table(df_trades.drop(columns=["Portfolio ID"]))
    else:
        st.info("No trades for this portfolio.")

    # === Add New Trade ===
    st.subheader("➕ Add a New Trade")
    stock_ticker = st.text_input("Stock Ticker (e.g., AAPL, TSLA, LLOY.L)")
    trade_type = st.radio("Trade Type", ["buy", "sell"])
    quantity = st.number_input("Quantity", min_value=1, step=1)
    price = st.number_input("Price per Share", min_value=0.01, step=0.01)
    transaction_cost = st.number_input("Transaction Cost", min_value=0.0, step=0.1)

    if st.button("Log Trade"):
        if stock_ticker and quantity > 0 and price > 0:
            db.add_trade(selected_portfolio_id, stock_ticker, trade_type, quantity, price, transaction_cost)
            st.success(f"Trade Logged: {trade_type.upper()} {quantity} {stock_ticker} @ ${price:.2f}")
            st.rerun()

    # === Data Visualization ===
    st.subheader("📊 Portfolio Analysis")

    # Portfolio Allocation Pie Chart
    if stocks:
        stock_counts = pd.Series([s[2] for s in stocks]).value_counts()
        fig1, ax1 = plt.subplots()
        ax1.pie(stock_counts, labels=stock_counts.index, autopct='%1.1f%%', startangle=90)
        ax1.set_title("Stock Allocation")
        st.pyplot(fig1)

    # Portfolio Value Line Chart (Simulated Data)
    if trades:
        df_trades["Cumulative Value"] = df_trades["Quantity"] * df_trades["Price"]
        df_trades["Date"] = pd.to_datetime(df_trades["Timestamp"])
        df_trades = df_trades.sort_values("Date")

        fig2, ax2 = plt.subplots()
        ax2.plot(df_trades["Date"], df_trades["Cumulative Value"].cumsum(), marker="o", linestyle="-", label="Portfolio Value Over Time")
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Cumulative Value ($)")
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
