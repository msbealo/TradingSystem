# main.py (or in your Streamlit app)

from database import TradingDatabase
from backtest_engine import BacktestEngine
import backtrader as bt

# 1) Initialize your DB
db = TradingDatabase()

# 2) Create your backtest engine
engine = BacktestEngine(db)

# 3) Define (or import) a sample strategy
class MyStrategy(bt.Strategy):
    params = (("period", 14),)
    def __init__(self):
        self.sma = bt.ind.SMA(period=self.p.period)
    def next(self):
        if self.data.close[0] > self.sma[0]:
            if not self.position:
                self.buy()
        else:
            if self.position:
                self.sell()

# 4) Prepare optional settings
strategy_params = {"period": 20}
broker_cfg = {"cash": 50000, "commission": 0.001}

# 5) Run the backtest
results = engine.run_backtest(
    strategy_class=MyStrategy,
    ticker="RCP.L",
    start_date="2020-01-02",
    end_date="2025-03-03",
    strategy_params=strategy_params,
    broker_settings=broker_cfg
)

# 6) Inspect results
final_value = results[0].broker.getvalue()
print("Final Portfolio Value:", final_value)
