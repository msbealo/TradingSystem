# data_fetcher.py

import datetime
import yfinance as yf
from database import TradingDatabase  # Import your DB class
import pandas as pd

class StockDataFetcher:
    """
    Handles downloading fundamental and price data from yfinance,
    checking the local SQLite database first to avoid unnecessary requests.
    """

    def __init__(self, db: TradingDatabase):
        self.db = db  # An instance of TradingDatabase

    def fetch_fundamental_data(self, ticker: str, force_refresh: bool = False):
        """
        Fetches fundamental data for a given ticker using yfinance,
        unless the data was last updated < 7 days ago and force_refresh=False.
        """
        last_updated_str = self.db.get_fundamentals_last_updated(ticker)
        if not force_refresh and last_updated_str:
            # Attempt to parse
            try:
                last_dt = datetime.datetime.fromisoformat(last_updated_str)
                age = datetime.datetime.now() - last_dt
                if age.days < 7:
                    print(f"Skipping {ticker}: fundamentals < 7 days old.")
                    return
            except ValueError:
                # If parse fails, ignore and do the fetch
                pass

        # parse and store ...
        self.db.update_fundamentals(
            ticker=ticker,
            # pass fields, etc...
        )
        
        print(f"🌐 Downloading fundamental data for {ticker} via yfinance...")
        info = yf.Ticker(ticker).info
        
        # 3. Parse key metrics safely
        market_cap = info.get("marketCap", None)
        pe_ratio = info.get("trailingPE", None)
        forward_pe = info.get("forwardPE", None)
        eps = info.get("trailingEps", None)
        price_to_book = info.get("priceToBook", None)
        price_to_sales = info.get("priceToSalesTrailing12Months", None)
        enterprise_to_ebitda = info.get("enterpriseToEbitda", None)

        # P/FCF => marketCap / freeCashflow if both present
        free_cash_flow = info.get("freeCashflow", None)
        price_to_fcf = None
        if market_cap and free_cash_flow and free_cash_flow != 0:
            price_to_fcf = market_cap / free_cash_flow

        net_profit_margin = info.get("profitMargins", None)
        return_on_equity = info.get("returnOnEquity", None)
        return_on_assets = info.get("returnOnAssets", None)
        # No direct ROIC in yfinance, store None or implement your own logic
        return_on_invested_capital = None

        # Growth metrics
        eps_growth = None  # Possibly from "earningsQuarterlyGrowth" or "earningsGrowth"
        if "earningsGrowth" in info:
            eps_growth = info["earningsGrowth"]  # yoy
        revenue_growth_yoy = info.get("revenueGrowth", None)
        earnings_growth_yoy = info.get("earningsGrowth", None)
        # 3-year growth often isn't in yfinance
        revenue_growth_3y = None
        eps_growth_3y = None

        # Dividend metrics
        dividend_yield = None
        if info.get("dividendYield") is not None:
            dividend_yield = float(info["dividendYield"] * 100)  # convert fraction to percent

        dividend_payout_ratio = info.get("payoutRatio", None)
        dividend_growth_5y = info.get("fiveYearAvgDividendYield", None)

        # Ratios
        debt_to_equity = info.get("debtToEquity", None)
        current_ratio = info.get("currentRatio", None)
        quick_ratio = info.get("quickRatio", None)
        # interestCoverage -> not in yfinance, so None
        interest_coverage = None

        # Market Cap
        #    Already stored in market_cap
        # free float
        free_float = info.get("floatShares", None)
        # Insider / institutional
        insider_ownership = info.get("heldPercentInsiders", None)
        institutional_ownership = info.get("heldPercentInstitutions", None)
        beta_val = info.get("beta", None)  # or "beta3Year"
        price_change_52w = info.get("52WeekChange", None)

        # 4. Update or insert fundamentals
        self.db.update_fundamentals(
            ticker=ticker,
            market_cap=market_cap,
            pe_ratio=pe_ratio,
            eps=eps,
            dividend_yield=dividend_yield,
            debt_to_equity=debt_to_equity,
            forward_pe=forward_pe,
            price_to_book=price_to_book,
            price_to_sales=price_to_sales,
            enterprise_to_ebitda=enterprise_to_ebitda,
            price_to_fcf=price_to_fcf,
            net_profit_margin=net_profit_margin,
            return_on_equity=return_on_equity,
            return_on_assets=return_on_assets,
            return_on_invested_capital=return_on_invested_capital,
            eps_growth=eps_growth,
            revenue_growth_yoy=revenue_growth_yoy,
            earnings_growth_yoy=earnings_growth_yoy,
            revenue_growth_3y=revenue_growth_3y,
            eps_growth_3y=eps_growth_3y,
            dividend_payout_ratio=dividend_payout_ratio,
            dividend_growth_5y=dividend_growth_5y,
            current_ratio=current_ratio,
            quick_ratio=quick_ratio,
            interest_coverage=interest_coverage,
            free_float=free_float,
            insider_ownership=insider_ownership,
            institutional_ownership=institutional_ownership,
            beta=beta_val,
            price_change_52w=price_change_52w
        )

    def fetch_price_data(self, ticker: str, start_date: str = "2000-01-01", force_refresh: bool = False):
        """
        Fetches historical price data from yfinance starting from 'start_date' to today,
        then updates the database. Checks for missing dates if not force_refresh.
        """
        print(f"🔍 Checking existing price data for {ticker}...")

        # 1. Get the latest date we have for this ticker
        existing_data = self.db.get_price_data(ticker)
        if existing_data and not force_refresh:
            # existing_data: list of rows -> (date, open, high, low, close, adj_close, volume)
            last_date_stored = existing_data[-1][0]  # the date of the last row
            last_date_dt = datetime.datetime.strptime(last_date_stored, "%Y-%m-%d")
            new_start_dt = last_date_dt + datetime.timedelta(days=1)
            start_date_str = new_start_dt.strftime("%Y-%m-%d")
            if new_start_dt > datetime.datetime.now():
                print(f"✅ {ticker}: We already have up-to-date price data.")
                return
            # Update 'start_date' with the next missing day
            print(f"⏩ Updating price data from {start_date_str} forward.")
            start_date = start_date_str
        else:
            print(f"ℹ️ No existing data for {ticker}, downloading from {start_date}.")

        # 2. Download from yfinance
        #    Use auto_adjust=False so we get an "Adj Close" column.
        #    If you prefer a single "Close" column already adjusted, use auto_adjust=True.
        print(f"🌐 Downloading price data for {ticker} from {start_date} to present.")
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=False)

        if df.empty:
            print(f"⚠️ Warning: No data received for {ticker} from yfinance.")
            return

        # 3. Flatten columns if we have a multi-index (e.g. ("Close", "VOD.L"))
        if isinstance(df.columns, pd.MultiIndex):
            # Typically, we drop level=1 to keep columns like "Close", "High", etc.
            # e.g. df.columns = df.columns.droplevel(level=1)
            df.columns = df.columns.droplevel(level=1)

        # 4. Parse data into dictionary rows
        price_rows = []
        for idx, row in df.iterrows():
            # If "Adj Close" is present, use it; otherwise fallback to "Close"
            adj_close = row["Adj Close"] if "Adj Close" in df.columns else row["Close"]

            price_rows.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open_price": row["Open"],
                "high_price": row["High"],
                "low_price": row["Low"],
                "close_price": row["Close"],
                "adjusted_close": adj_close,
                "volume": int(row["Volume"]) if not pd.isnull(row["Volume"]) else 0
            })

        # 5. Insert/Update in DB
        self.db.store_price_data(ticker, price_rows)
        print(f"✅ Price data stored/updated for {ticker}.")

    def sync_stock_info(self, ticker: str, company_name=None, sector=None):
        """
        Ensures the 'stocks' table has an entry for this ticker.
        Then fetches fundamentals, and optionally some initial price data.
        """
        # 1. Insert/Update in the 'stocks' table
        self.db.add_master_stock(ticker, company_name, sector)
        # 2. Fetch & update fundamentals (only if needed)
        self.fetch_fundamental_data(ticker)
