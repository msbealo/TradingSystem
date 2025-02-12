import streamlit as st

# Set page title
st.set_page_config(page_title="AI-Powered UK Trading System", layout="wide")

# Welcome message
st.title("AI-Powered UK Stock Trading System")
st.write("Welcome to the AI-powered trading system. This is the first step toward building an automated trading platform.")

# Button to confirm setup
if st.button("Check System Setup"):
    st.success("Your environment is correctly set up! 🚀")

