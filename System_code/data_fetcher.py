# data_fetcher.py

import datetime
import yfinance as yf
from database import TradingDatabase  # Import your DB class
import pandas as pd
import json
import os

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
        Then dynamically upserts the row into the 'fundamentals' table.
        """
        last_updated_str = self.db.get_fundamentals_last_updated(ticker)
        if not force_refresh and last_updated_str:
            try:
                last_dt = datetime.datetime.fromisoformat(last_updated_str)
                age = datetime.datetime.now() - last_dt
                if age.days < 7:
                    print(f"Skipping {ticker}: fundamentals < 7 days old.")
                    return
            except ValueError:
                pass

        print(f"🌐 Downloading fundamental data for {ticker} via yfinance...")
        info = yf.Ticker(ticker).info

        # Dynamically build a dictionary of fundamentals, including at least 'ticker'
        now_str = datetime.datetime.now().isoformat()
        fundamentals_dict = {
            # Core metrics
            "ticker": ticker,
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": float(info["dividendYield"] * 100) if info.get("dividendYield") is not None else None,
            "debt_to_equity": info.get("debtToEquity"),
            "last_updated": datetime.datetime.now().isoformat(),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "enterprise_to_ebitda": info.get("enterpriseToEbitda"),
            "free_cash_flow": info.get("freeCashflow"),
            "price_to_fcf": None,  # We'll compute it below, if possible
            "net_profit_margin": info.get("profitMargins"),
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "return_on_invested_capital": None,  # Not provided by yfinance, set to None

            # Growth metrics
            "eps_growth": info.get("earningsGrowth"),
            "revenue_growth_yoy": info.get("revenueGrowth"),
            "earnings_growth_yoy": info.get("earningsGrowth"),
            "revenue_growth_3y": None,
            "eps_growth_3y": None,

            # Dividend metrics
            "dividend_payout_ratio": info.get("payoutRatio"),
            "dividend_growth_5y": info.get("fiveYearAvgDividendYield"),

            # Ratios
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "interest_coverage": None,
            "free_float": info.get("floatShares"),
            "insider_ownership": info.get("heldPercentInsiders"),
            "institutional_ownership": info.get("heldPercentInstitutions"),
            "beta": info.get("beta"),
            "price_change_52w": info.get("52WeekChange"),

            # Extra fields from raw info
            "max_age": info.get("maxAge"),
            "price_hint": info.get("priceHint"),
            "previous_close": info.get("previousClose"),
            "open_price": info.get("open"),
            "day_low": info.get("dayLow"),
            "day_high": info.get("dayHigh"),
            "regular_market_previous_close": info.get("regularMarketPreviousClose"),
            "regular_market_open": info.get("regularMarketOpen"),
            "regular_market_day_low": info.get("regularMarketDayLow"),
            "regular_market_day_high": info.get("regularMarketDayHigh"),
            "regular_market_volume": info.get("regularMarketVolume"),
            "average_volume": info.get("averageVolume"),
            "average_volume_10days": info.get("averageVolume10days"),
            "average_daily_volume_10day": info.get("averageDailyVolume10Day"),
            "bid": info.get("bid"),
            "ask": info.get("ask"),
            "bid_size": info.get("bidSize"),
            "ask_size": info.get("askSize"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_day_average": info.get("fiftyDayAverage"),
            "two_hundred_day_average": info.get("twoHundredDayAverage"),
            "trailing_annual_dividend_rate": info.get("trailingAnnualDividendRate"),
            "trailing_annual_dividend_yield": info.get("trailingAnnualDividendYield"),
            "currency": info.get("currency"),
            "tradeable": 1 if info.get("tradeable") else 0,
            "quote_type": info.get("quoteType"),
            "current_price": info.get("currentPrice"),
            "target_high_price": info.get("targetHighPrice"),
            "target_low_price": info.get("targetLowPrice"),
            "target_mean_price": info.get("targetMeanPrice"),
            "target_median_price": info.get("targetMedianPrice"),
            "recommendation_key": info.get("recommendationKey"),
            "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
            "financial_currency": info.get("financialCurrency"),
            "symbol": info.get("symbol"),
            "language": info.get("language"),
            "region": info.get("region"),
            "type_disp": info.get("typeDisp"),
            "quote_source_name": info.get("quoteSourceName"),
            "triggerable": 1 if info.get("triggerable") else 0,
            "custom_price_alert_confidence": info.get("customPriceAlertConfidence"),
            "market_state": info.get("marketState"),
            "long_name": info.get("longName"),
            "regular_market_change_percent": info.get("regularMarketChangePercent"),
            "short_name": info.get("shortName"),
            "regular_market_time": info.get("regularMarketTime"),
            "exchange": info.get("exchange"),
            "message_board_id": info.get("messageBoardId"),
            "exchange_timezone_name": info.get("exchangeTimezoneName"),
            "exchange_timezone_short_name": info.get("exchangeTimezoneShortName"),
            "gmt_offset_milliseconds": info.get("gmtOffSetMilliseconds"),
            "market": info.get("market"),
            "esg_populated": 1 if info.get("esgPopulated") else 0,
            "corporate_actions": json.dumps(info.get("corporateActions", [])),
            "has_pre_post_market_data": 1 if info.get("hasPrePostMarketData") else 0,
            "first_trade_date_milliseconds": info.get("firstTradeDateMilliseconds"),
            "regular_market_change": info.get("regularMarketChange"),
            "regular_market_day_range": info.get("regularMarketDayRange"),
            "full_exchange_name": info.get("fullExchangeName"),
            "average_daily_volume_3month": info.get("averageDailyVolume3Month"),
            "fifty_two_week_low_change": info.get("fiftyTwoWeekLowChange"),
            "fifty_two_week_low_change_percent": info.get("fiftyTwoWeekLowChangePercent"),
            "fifty_two_week_range": info.get("fiftyTwoWeekRange"),
            "fifty_two_week_high_change": info.get("fiftyTwoWeekHighChange"),
            "fifty_two_week_high_change_percent": info.get("fiftyTwoWeekHighChangePercent"),
            "fifty_two_week_change_percent": info.get("52WeekChangePercent"),
            "earnings_timestamp_start": info.get("earningsTimestampStart"),
            "earnings_timestamp_end": info.get("earningsTimestampEnd"),
            "is_earnings_date_estimate": 1 if info.get("isEarningsDateEstimate") else 0,
            "eps_trailing_twelve_months": info.get("epsTrailingTwelveMonths"),
            "eps_forward": info.get("epsForward"),
            "eps_current_year": info.get("epsCurrentYear"),
            "price_eps_current_year": info.get("priceEpsCurrentYear"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "book_value": info.get("bookValue"),
            "fifty_day_average_change": info.get("fiftyDayAverageChange"),
            "fifty_day_average_change_percent": info.get("fiftyDayAverageChangePercent"),
            "two_hundred_day_average_change": info.get("twoHundredDayAverageChange"),
            "two_hundred_day_average_change_percent": info.get("twoHundredDayAverageChangePercent"),
            "source_interval": info.get("sourceInterval"),
            "exchange_data_delayed_by": info.get("exchangeDataDelayedBy"),
            "crypto_tradeable": 1 if info.get("cryptoTradeable") else 0,
            "trailing_peg_ratio": info.get("trailingPegRatio"),
            "industry": info.get("industry"),
            "sector": info.get("sector"),
        }

            # Example of computing derived metrics like price_to_fcf:
        market_cap = fundamentals_dict["market_cap"]
        free_cash_flow = info.get("freeCashflow")
        if market_cap and free_cash_flow and free_cash_flow != 0:
            fundamentals_dict["price_to_fcf"] = market_cap / free_cash_flow
        else:
            fundamentals_dict["price_to_fcf"] = None

        print(f"Ticker: {ticker}, Industry: {info.get('industry')}, Sector: {info.get('sector')}")

        # Use your new dynamic method to upsert the fundamentals
        self.db.update_fundamentals(fundamentals_dict)

        # (Optional) Debug log
        # If you want to write raw info to a file, you can do so here:
        if False:  # set to True if you want to enable
            debug_file_path = "debug_fundamentals.json"
            info_obj = {
                "ticker": ticker,
                "timestamp": now_str,
                "info": info
            }
            with open(debug_file_path, "a", encoding="utf-8") as debugf:
                debugf.write(json.dumps(info_obj, ensure_ascii=False) + "\n")

        return info

    def fetch_price_data(self, ticker: str, start_date: str = "2000-01-01", force_refresh: bool = False):
        """
        Fetches historical price data from yfinance starting from the provided start_date.
        If data already exists in the database and force_refresh is False, the method:
        - Downloads any missing historical data before the earliest date stored (if the user-specified start_date is earlier).
        - Downloads new data after the latest stored date.
        The downloaded data is then stored/updated in the database.
        """
        import datetime
        import pandas as pd
        import yfinance as yf

        print(f"🔍 Checking existing price data for {ticker}...")
        existing_data = self.db.get_price_data(ticker)
        
        # Helper function to convert a DataFrame into a list of row dicts
        def process_df_to_rows(df):
            rows = []
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(level=1)
            for idx, row in df.iterrows():
                adj_close = row["Adj Close"] if "Adj Close" in df.columns else row["Close"]
                rows.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open_price": row["Open"],
                    "high_price": row["High"],
                    "low_price": row["Low"],
                    "close_price": row["Close"],
                    "adjusted_close": adj_close,
                    "volume": int(row["Volume"]) if not pd.isnull(row["Volume"]) else 0
                })
            return rows

        price_rows_to_update = []

        if existing_data and not force_refresh:
            # Convert dates in existing data to datetime objects
            existing_dates = [datetime.datetime.strptime(row[0], "%Y-%m-%d") for row in existing_data]
            earliest_date = min(existing_dates)
            latest_date = max(existing_dates)
            user_start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            
            # 1. Check if there's a gap at the beginning.
            if user_start_dt < earliest_date:
                end_dt = earliest_date - datetime.timedelta(days=1)
                end_date_str = end_dt.strftime("%Y-%m-%d")
                print(f"⏩ Downloading missing historical data for {ticker} from {start_date} to {end_date_str}.")
                df_early = yf.download(ticker, start=start_date, end=end_date_str, progress=False, auto_adjust=False)
                if not df_early.empty:
                    early_rows = process_df_to_rows(df_early)
                    price_rows_to_update.extend(early_rows)
                else:
                    print(f"⚠️ No early data available for {ticker} from {start_date} to {end_date_str}.")

            # 2. Check for forward update (data after the latest stored date)
            new_start_dt = latest_date + datetime.timedelta(days=1)
            if new_start_dt < datetime.datetime.now():
                new_start_str = new_start_dt.strftime("%Y-%m-%d")
                print(f"⏩ Updating price data for {ticker} from {new_start_str} forward.")
                df_forward = yf.download(ticker, start=new_start_str, progress=False, auto_adjust=False)
                if not df_forward.empty:
                    forward_rows = process_df_to_rows(df_forward)
                    price_rows_to_update.extend(forward_rows)
                else:
                    print(f"✅ {ticker}: Forward data is already up-to-date.")
            
            if price_rows_to_update:
                self.db.store_price_data(ticker, price_rows_to_update)
                print(f"✅ Price data updated for {ticker}.")
            else:
                print(f"✅ {ticker}: Price data is already up-to-date.")
        else:
            # No existing data or force refresh requested: download everything from start_date.
            print(f"ℹ️ No existing data for {ticker} or force refresh requested, downloading from {start_date}.")
            df = yf.download(ticker, start=start_date, progress=False, auto_adjust=False)
            if df.empty:
                # Fallback: try period='max' to see if any data is available.
                print(f"⚠️ No data received for {ticker} from {start_date}. Attempting to fetch full history.")
                df = yf.download(ticker, period="max", progress=False, auto_adjust=False)
                if df.empty:
                    print(f"⚠️ No historical data available for {ticker}.")
                    return
                else:
                    available_start = df.index.min().strftime("%Y-%m-%d")
                    print(f"ℹ️ Data for {ticker} is available from {available_start} onward.")
            price_rows = process_df_to_rows(df)
            self.db.store_price_data(ticker, price_rows)
            print(f"✅ Price data stored for {ticker}.")
    
    def sync_stock_info(self, ticker: str, company_name=None, sector=None):
        """
        Ensures the 'stocks' table has an entry for this ticker.
        Then fetches fundamentals, and optionally some initial price data.
        """
        # 1. Insert/Update in the 'stocks' table
        self.db.add_master_stock(ticker, company_name, sector)
        # 2. Fetch & update fundamentals (only if needed)
        self.fetch_fundamental_data(ticker)
