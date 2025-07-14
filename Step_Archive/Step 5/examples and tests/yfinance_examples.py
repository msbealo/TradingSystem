import yfinance as yf
import pandas as pd

ticker_symbol = "VOD.L"  # Example for Vodafone on LSE

df = yf.download(ticker_symbol, start="2023-01-01", end="2023-03-01", auto_adjust=False)

# Drop the Ticker level (level=1)
df.columns = df.columns.droplevel(level=1)

# Then remove the column index name (which is "Price") if you prefer no name at all:
df.columns.name = None

print(df.head())
print(df.columns)

print("Number of levels:", df.columns.nlevels)
print("df.columns:", df.columns)