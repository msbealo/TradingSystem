import streamlit as st
from backtesting import run_backtest 

st.title("Portfolio Backtesting")

# Select a portfolio
portfolio_id = st.selectbox("Select Portfolio", [1, 2, 3])  # Example portfolio IDs

# Fetch AI-generated strategies
strategies = [{"strategy_name": "Momentum Strategy", "json": {
    "strategy_name": "Momentum Strategy",
    "indicators": [{"type": "RSI", "parameters": {"period": 14}, "condition": "<", "value": 30}],
    "entry_condition": "all",
    "exit_condition": {"type": "RSI", "parameters": {"period": 14}, "condition": ">", "value": 70}
}}]

selected_strategy = st.selectbox("Select Strategy", [s["strategy_name"] for s in strategies])

if st.button("Run Backtest"):
    strategy_json = next(s["json"] for s in strategies if s["strategy_name"] == selected_strategy)
    run_backtest(portfolio_id, strategy_json)
