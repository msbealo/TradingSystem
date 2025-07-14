import os
import pandas as pd

FOLDER = "Strategy_Trade_History"

def analyze_file(filepath):
    try:
        df = pd.read_csv(filepath)

        if 'position_size' not in df.columns or 'close' not in df.columns:
            return (os.path.basename(filepath), 'Missing columns', None)

        # Count trades based on position_size changes
        position_changes = df['position_size'].diff().fillna(0) != 0
        trade_count = position_changes.sum()

        # Cumulative return based on first and last closing price
        if len(df['close']) < 2:
            cumulative_return = None
        else:
            cumulative_return = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100

        return (os.path.basename(filepath), int(trade_count), round(cumulative_return, 2) if cumulative_return is not None else 'N/A')
    
    except Exception as e:
        return (os.path.basename(filepath), f'Error: {e}', None)

def main():
    print(f"{'File':<45} {'Trades':>8} {'Cumulative Return (%)':>24}")
    print("-" * 80)

    for filename in os.listdir(FOLDER):
        if filename.lower().endswith(".csv"):
            filepath = os.path.join(FOLDER, filename)
            name, trades, cum_return = analyze_file(filepath)

            trades_display = f"\033[91m{trades}\033[0m" if trades == 0 else trades  # Red highlight if zero trades
            print(f"{name:<45} {str(trades_display):>8} {str(cum_return):>24}")

if __name__ == "__main__":
    main()
