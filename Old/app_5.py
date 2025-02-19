import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
from database import TradingDatabase  # Import the TradingDatabase class
from chatgpt_api import generate_trading_strategy  # Import AI strategy function

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

# === AI-Generated Strategy Feature ===
st.subheader("💡 AI-Generated Trading Strategies")

user_strategy_input = st.text_area("Describe your trading strategy in plain English:", 
                                   placeholder="Example: Create a momentum strategy using RSI and MACD.")

if st.button("Generate Strategy"):
    if user_strategy_input.strip():
        strategy = generate_trading_strategy(user_strategy_input)
        if "error" in strategy:
            st.error("⚠️ Strategy generation failed: " + strategy["error"])
        else:
            st.json(strategy)  # Display JSON response
            
            # Create human-readable summary
            st.subheader("📄 Strategy Summary")
            st.write(f"**Strategy Name:** {strategy['strategy_name']}")
            st.write(f"**Description:** {strategy['description']}")
            st.write("**Indicators Used:**")
            for indicator in strategy["indicators"]:
                st.write(f"- {indicator['type']} ({indicator['parameters']})")
            st.write(f"**Entry Condition:** {strategy['entry_condition']}")
            st.write(f"**Exit Condition:** {strategy['exit_condition']['type']} {strategy['exit_condition']['condition']} {strategy['exit_condition']['value']}")
            st.write(f"**Risk Management:** Stop-Loss: {strategy['risk_management']['stop_loss']}, Take-Profit: {strategy['risk_management']['take_profit']}, Position Size: {strategy['risk_management']['position_size']}")
            
            # Save strategy to database option
            if st.button("Save Strategy to Database"):
                portfolio_id = st.selectbox("Assign Strategy to Portfolio", [p[0] for p in portfolios])
                if portfolio_id:
                    db.add_strategy(portfolio_id, strategy["strategy_name"], json.dumps(strategy))
                    st.success(f"Strategy '{strategy['strategy_name']}' saved successfully!")
    else:
        st.warning("Please enter a trading idea.")

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
        st.subheader("📊 Performance Metrics")
        st.write(f"Initial Capital: **${initial_capital:,.2f}**")
        st.write(f"Current Value: **${portfolio_value:,.2f}**")
        st.write(f"Total Return: **{return_percentage:.2f}%**")

# === Clean Up Database ===
st.sidebar.subheader("Database Maintenance")
if st.sidebar.button("Clean Database (Remove Orphans)"):
    db.clean_database()
    st.sidebar.success("Database cleaned!")

# Close database connection
db.close_connection()
