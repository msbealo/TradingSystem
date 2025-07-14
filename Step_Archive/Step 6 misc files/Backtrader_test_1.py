import backtrader as bt
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# -------------------------
# Custom Commission Scheme
# -------------------------
class CustomCommission(bt.CommInfoBase):
    params = (('commission', 0.001), ('tier_threshold', 10000), ('high_commission', 0.002))

    def _getcommission(self, size, price, pseudoexec):
        commission = self.p.commission if abs(size) <= self.p.tier_threshold else self.p.high_commission
        return abs(size) * price * commission

# -------------------------
# Custom Position Sizing Indicator
# -------------------------
class RiskAdjustedSizer(bt.Sizer):
    params = (('risk_percent', 0.02), ('stop_distance', 0.02))

    def _getsizing(self, comminfo, cash, data, isbuy):
        # Example logic
        price = data.close[0]
        stop_price = price * (1 - self.p.stop_distance)
        risk_amount = cash * self.p.risk_percent

        # Avoid dividing by zero or negative (if price < stop_price).
        if (price - stop_price) <= 0:
            return 1

        size = risk_amount / (price - stop_price)

        # Return an integer number of shares
        return max(1, int(size))

# -------------------------
# Custom Performance Analyzer
# -------------------------
class CustomPerformanceAnalyzer(bt.Analyzer):
    def __init__(self):
        self.win_trades = 0
        self.loss_trades = 0
        self.total_return = 0.0

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnl
            if pnl > 0:
                self.win_trades += 1
            else:
                self.loss_trades += 1
            self.total_return += pnl

    def get_analysis(self):
        total_trades = self.win_trades + self.loss_trades
        win_rate = self.win_trades / total_trades if total_trades > 0 else 0
        return {
            'total_return': self.total_return,
            'win_rate': win_rate,
            'total_trades': total_trades
        }

# -------------------------
# Advanced Strategy
# -------------------------
class MovingAverageCrossoverStrategy(bt.Strategy):
    params = (('fast_period', 10), ('slow_period', 30),
              ('stop_loss', 0.02), ('take_profit', 0.04))

    def __init__(self):
        self.fast_ma = bt.ind.SMA(self.data, period=self.p.fast_period)
        self.slow_ma = bt.ind.SMA(self.data, period=self.p.slow_period)
        # Sizing is determined externally by the Sizer we added to cerebro

    def next(self):
        if not self.position:  # no open position
            if self.fast_ma[0] > self.slow_ma[0]:
                self.buy_bracket(
                    # No manual "size" param needed if the sizer is used
                    price=self.data.close[0],
                    stopprice=self.data.close[0] * (1 - self.p.stop_loss),
                    limitprice=self.data.close[0] * (1 + self.p.take_profit)
                )

# -------------------------
# Data Download and Preparation
# -------------------------
def download_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    daily_data = yf.download('AAPL', group_by="column", start=start_date, end=end_date, interval='1d', auto_adjust=False)

    daily_data.columns = daily_data.columns.droplevel(1)

    print(daily_data.head())       # Check if data is empty
    print(daily_data.columns)      # See actual column names

    daily_data.reset_index(inplace=True)
    daily_data['Date'] = pd.to_datetime(daily_data['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    daily_data.dropna(subset=['Date'], inplace=True)
    daily_data = daily_data[['Date','Open','High','Low','Close','Volume']]

    print(daily_data.head())       # Check if data is empty
    print(daily_data.columns)      # See actual column names

    file_path = os.path.join(os.getcwd(), 'AAPL_daily.csv')
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        daily_data.to_csv(f, index=False, lineterminator='\n')

    # with open('AAPL_daily.csv') as f:
    #     for line in f:
    #         print(repr(line))

# -------------------------
# Backtesting Setup
# -------------------------
def run_backtest():
    cerebro = bt.Cerebro(optreturn=False)

    data = bt.feeds.GenericCSVData(
        dataname='AAPL_daily.csv',
        timeframe=bt.TimeFrame.Days,
        compression=1,
        dtformat='%Y-%m-%d',
        header=1,
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        openinterest=-1
    )

    cerebro.addsizer(RiskAdjustedSizer)
    cerebro.adddata(data)
    cerebro.broker.addcommissioninfo(CustomCommission())
    cerebro.addstrategy(MovingAverageCrossoverStrategy)
    cerebro.addanalyzer(CustomPerformanceAnalyzer, _name='performance')
    cerebro.broker.set_cash(100000)

    results = cerebro.run(maxcpus=1)

    for strat in results:
        analysis = strat.analyzers.performance.get_analysis()
        print(f"Total Return: {analysis['total_return']:.2f}, "
              f"Win Rate: {analysis['win_rate']:.2%}, "
              f"Total Trades: {analysis['total_trades']}")

    cerebro.plot()

# Execute data download and backtest
if __name__ == "__main__":
    download_data()
    run_backtest()