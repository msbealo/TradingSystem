# backtest_engine.py

import matplotlib
matplotlib.use('Agg')  # Use a non-GUI backend suitable for Streamlit
import matplotlib.pyplot as plt
import backtrader as bt
import pandas as pd

class PortfolioAnalyzer(bt.Analyzer):
    def __init__(self):
        self.start_value = None
        self.end_value = None

    def start(self):
        self.start_value = self.strategy.broker.getvalue()

    def stop(self):
        self.end_value = self.strategy.broker.getvalue()

    def get_analysis(self):
        return {
            'start': self.start_value,
            'end': self.end_value,
            'return': (self.end_value / self.start_value - 1) * 100
        }

class BacktsestEngine:
    def __init__(self, db):
        self.db = db

    def _create_pandas_feed(self, ticker, start_date=None, end_date=None):
        df = self.db.get_price_dataframe(ticker, start_date, end_date)
        if df.empty:
            raise ValueError(f"No price data for {ticker}.")
        return bt.feeds.PandasData(dataname=df)

    def run_portfolio_backtest(self, portfolio, strategies, start_date=None, end_date=None):
         # This list holds brief info needed for portfolio-level metrics
        analysis_list = []
        # This list holds detailed info (e.g., trade logs, charts) for display
        all_details = []
                      
        initial_capital = portfolio['capital']
        capital_per_strategy = initial_capital / len(strategies)

        for strategy in strategies:
            assigned_stocks = strategy['stocks']
            capital_per_stock = capital_per_strategy / len(assigned_stocks)

            for stock in assigned_stocks:
                cerebro = bt.Cerebro(cheat_on_open=True)

                # Setup data feed
                data_feed = self._create_pandas_feed(stock, start_date, end_date)
                cerebro.adddata(data_feed)

                # Set capital allocation
                cerebro.broker.setcash(capital_per_stock)

                # Attach strategy dynamically
                strat_class = strategy['class']
                cerebro.addstrategy(strat_class)

                # Add analyzers for performance metrics
                cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
                cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
                cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
                cerebro.addanalyzer(PortfolioAnalyzer, _name='portfolio')

                # Observers for visual markers on the chart
                cerebro.addobserver(bt.observers.Trades)
                cerebro.addobserver(bt.observers.BuySell)

                # 6) Run the backtest
                backtest_results = cerebro.run(show=False)
                result = backtest_results[0]  # The single Strategy object
                
                if hasattr(result, '_final_logs'):
                    daily_log_list = result._final_logs  # list of dicts
                    daily_log_df = pd.DataFrame(daily_log_list)
                else:
                    daily_log_df = pd.DataFrame()  # if none

                # 7) Generate a Matplotlib figure (avoid calling cerebro.plot() directly)
                fig = []
                figs = cerebro.plot(iplot=False, show=False)  
                # Typically returns a list of (figure, axes). For one data feed, we can do:
                fig = figs[0][0]  # the first (fig, axes) tuple

                # 8) Store metrics in a minimal dict for later portfolio-level aggregation
                analysis_list.append({
                    'strategy': strategy['name'],
                    'stock': stock,
                    'analyzers': result.analyzers
                })

                # 9) Build a trade history DataFrame if desired
                trades_analyzer = result.analyzers.trades.get_analysis()
                trades_df = self._build_trades_dataframe(trades_analyzer)

                # 10) Retrieve the original price data for reference or exporting
                price_df = self.db.get_price_dataframe(stock, start_date, end_date)

                # 11) Store all detailed info for Streamlit
                all_details.append({
                    'strategy': strategy['name'],
                    'stock': stock,
                    'chart_fig': fig,
                    'trades_df': trades_df,
                    'price_df': price_df,
                    'indicator_log_df': daily_log_df  # <-- new
                })

        # 12) Aggregate results at the portfolio level
        portfolio_summary = self._aggregate_portfolio_results(analysis_list)
        # Attach our per-strategy, per-stock detail
        portfolio_summary["detailed_results"] = all_details

        return portfolio_summary

    def _build_trades_dataframe(self, trades_analyzer):
        """
        Example helper method to parse the TradeAnalyzer output into a DataFrame.
        This can be as detailed or as simple as you prefer.
        """
        # trades_analyzer is a dict-like structure from Backtrader’s TradeAnalyzer
        # For example, you might parse winners, losers, total trades, etc.
        # Here’s a minimal example, returning a placeholder:
        trades_data = []

        won = trades_analyzer.get('won', {}).get('total', 0)
        lost = trades_analyzer.get('lost', {}).get('total', 0)
        total = won + lost

        trades_data.append({
            "Total Trades": total,
            "Winning Trades": won,
            "Losing Trades": lost
        })

        return pd.DataFrame(trades_data)


    def _aggregate_portfolio_results(self, results):
        """Combine results into portfolio-level metrics."""
        combined = {
            'cumulative_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

        for res in results:
            analyzers = res['analyzers']
            
            # Cumulative Return
            portfolio_data = analyzers.portfolio.get_analysis()
            combined['cumulative_return'] += portfolio_data['return']
            
            # Sharpe Ratio
            sharpe = analyzers.sharpe.get_analysis().get('sharperatio', 0)
            portfolio_return = analyzers.portfolio.get_analysis().get('return', 0)

            # Use the capital allocated to this test for weighting
            capital_weight = portfolio_return if portfolio_return > 0 else 1e-6  # Prevent division by zero
            sharpe = analyzers.sharpe.get_analysis().get('sharperatio', 0)
            if sharpe is None:
                sharpe = 0.0  # or handle it however you prefer
            combined['sharpe_ratio'] += (sharpe * capital_weight)

            # Track the total weights for final averaging
            combined.setdefault('sharpe_weight_total', 0)
            combined['sharpe_weight_total'] += capital_weight
            
            # Max Drawdown
            drawdown = analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
            combined['max_drawdown'] = max(combined['max_drawdown'], drawdown)

            # Win/Loss Rate
            trade_analysis = analyzers.trades.get_analysis()
            won = trade_analysis.get('won', {}).get('total', 0)
            lost = trade_analysis.get('lost', {}).get('total', 0)

            combined['total_trades'] += won + lost
            combined['winning_trades'] += won
            combined['losing_trades'] += lost

        # Compute weighted average Sharpe ratio
        if combined.get('sharpe_weight_total', 0) > 0:
            combined['sharpe_ratio'] /= combined['sharpe_weight_total']
        else:
            combined['sharpe_ratio'] = 0

        # Calculate final metrics
        if combined['total_trades'] > 0:
            combined['win_rate'] = (combined['winning_trades'] / combined['total_trades']) * 100

        return combined
