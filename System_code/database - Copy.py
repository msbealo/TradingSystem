import sqlite3
import json
import datetime
import pandas as pd

DB_FILE = "trading_system.db"

class TradingDatabase:
    def __init__(self):
        """Initialize the database connection and create tables if needed."""
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """
        Creates all necessary tables if they don't exist.
        This includes new tables for master stock info, fundamentals, and historical prices.
        Also preserves existing tables: portfolios, portfolio_stocks (renamed), strategies, trades.
        """
        print("📌 Debug: Checking or creating tables...")

        # ---------------------------
        # Portfolios Table
        # ---------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                capital REAL NOT NULL,
                execution_mode TEXT CHECK(execution_mode IN ('paper', 'live')) NOT NULL
            )
        ''')

        # ---------------------------
        # Portfolio_Stocks Table (REPLACES the old "stocks" table)
        # ---------------------------
        # This table ties a specific stock (by ticker or ID) to a portfolio.
        # We keep the old method signatures (add_stock, get_stocks) for compatibility.
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                stock_ticker TEXT NOT NULL
            )
        ''')

        # ---------------------------
        # Master Stocks Table
        # ---------------------------
        # Minimal info, linked to fundamentals / historical_prices by ticker.
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                company_name TEXT,
                sector TEXT
            )
        ''')

        # --------------------------------------------------
        # Stock Screens Table
        # --------------------------------------------------
        # This table stores user-defined stock screening criteria.
        # Criteria are stored as JSON strings.
        # --------------------------------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_screens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,  
                criteria TEXT NOT NULL,  -- JSON-encoded screening conditions
                stock_limit INTEGER,  -- Maximum number of stocks to return (NULL = no limit)
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # --------------------------------------------------
        # Portfolio Screens Table
        # --------------------------------------------------
        # This table links portfolios to stock screens.
        # It allows a portfolio to reference multiple screens.
        # Note: The "created_at" field is automatically set to the current timestamp.
        # --------------------------------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_screens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                screen_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
                FOREIGN KEY (screen_id) REFERENCES stock_screens(id) ON DELETE CASCADE
            )
        ''')


        # ---------------------------
        # Fundamentals Table
        # ---------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fundamentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,  -- ties to stocks.ticker

                -- Core metrics
                market_cap REAL,
                pe_ratio REAL,
                eps REAL,
                dividend_yield REAL,
                debt_to_equity REAL,
                last_updated DATETIME,

                -- Existing additional metrics
                forward_pe REAL,
                price_to_book REAL,
                price_to_sales REAL,
                enterprise_to_ebitda REAL,
                price_to_fcf REAL,
                net_profit_margin REAL,
                return_on_equity REAL,
                return_on_assets REAL,
                return_on_invested_capital REAL,
                eps_growth REAL,
                revenue_growth_yoy REAL,
                earnings_growth_yoy REAL,
                revenue_growth_3y REAL,
                eps_growth_3y REAL,
                dividend_payout_ratio REAL,
                dividend_growth_5y REAL,
                current_ratio REAL,
                quick_ratio REAL,
                interest_coverage REAL,
                free_float REAL,
                insider_ownership REAL,
                institutional_ownership REAL,
                beta REAL,
                price_change_52w REAL,

                -- New fields from raw info
                max_age INTEGER,
                price_hint INTEGER,
                previous_close REAL,
                open_price REAL,
                day_low REAL,
                day_high REAL,
                regular_market_previous_close REAL,
                regular_market_open REAL,
                regular_market_day_low REAL,
                regular_market_day_high REAL,
                regular_market_volume INTEGER,
                average_volume INTEGER,
                average_volume_10days INTEGER,
                average_daily_volume_10day INTEGER,
                bid REAL,
                ask REAL,
                bid_size INTEGER,
                ask_size INTEGER,
                fifty_two_week_low REAL,
                fifty_two_week_high REAL,
                fifty_day_average REAL,
                two_hundred_day_average REAL,
                trailing_annual_dividend_rate REAL,
                trailing_annual_dividend_yield REAL,
                currency TEXT,
                tradeable INTEGER,
                quote_type TEXT,
                current_price REAL,
                target_high_price REAL,
                target_low_price REAL,
                target_mean_price REAL,
                target_median_price REAL,
                recommendation_key TEXT,
                number_of_analyst_opinions INTEGER,
                financial_currency TEXT,
                symbol TEXT,
                language TEXT,
                region TEXT,
                type_disp TEXT,
                quote_source_name TEXT,
                triggerable INTEGER,
                custom_price_alert_confidence TEXT,
                market_state TEXT,
                long_name TEXT,
                regular_market_change_percent REAL,
                short_name TEXT,
                regular_market_time INTEGER,
                exchange TEXT,
                message_board_id TEXT,
                exchange_timezone_name TEXT,
                exchange_timezone_short_name TEXT,
                gmt_offset_milliseconds INTEGER,
                market TEXT,
                esg_populated INTEGER,
                corporate_actions TEXT,
                has_pre_post_market_data INTEGER,
                first_trade_date_milliseconds INTEGER,
                regular_market_change REAL,
                regular_market_day_range TEXT,
                full_exchange_name TEXT,
                average_daily_volume_3month INTEGER,
                fifty_two_week_low_change REAL,
                fifty_two_week_low_change_percent REAL,
                fifty_two_week_range TEXT,
                fifty_two_week_high_change REAL,
                fifty_two_week_high_change_percent REAL,
                fifty_two_week_change_percent REAL,
                earnings_timestamp_start INTEGER,
                earnings_timestamp_end INTEGER,
                is_earnings_date_estimate INTEGER,
                eps_trailing_twelve_months REAL,
                eps_forward REAL,
                eps_current_year REAL,
                price_eps_current_year REAL,
                shares_outstanding INTEGER,
                book_value REAL,
                fifty_day_average_change REAL,
                fifty_day_average_change_percent REAL,
                two_hundred_day_average_change REAL,
                two_hundred_day_average_change_percent REAL,
                source_interval INTEGER,
                exchange_data_delayed_by INTEGER,
                crypto_tradeable INTEGER,
                trailing_peg_ratio REAL,
                industry TEXT,
                sector TEXT
            )
        ''')

        # ---------------------------
        # Historical Prices Table
        # ---------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,        -- ties to stocks.ticker
                date DATE NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                adjusted_close REAL,
                volume INTEGER
            )
        ''')

        # ---------------------------
        # Strategies Table
        # ---------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                parameters TEXT NOT NULL  -- JSON stored as TEXT
            )
        ''')

        # ---------------------------
        # Portfolio_Strategies Table
        # ---------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                strategy_id INTEGER NOT NULL,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
                FOREIGN KEY (strategy_id) REFERENCES strategies(id)
            )
        ''')

        # ---------------------------
        # Trades Table
        # ---------------------------
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                stock_ticker TEXT NOT NULL,
                trade_type TEXT CHECK(trade_type IN ('buy', 'sell')) NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                transaction_cost REAL DEFAULT 0.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.check_tables()
        self.conn.commit()

    def check_tables(self):
        """Check if tables exist in the database."""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = self.cursor.fetchall()
        print(f"📌 Debug: Existing tables in database: {tables}")

    # -------------------------------------------------------------------------
    # PORTFOLIO MANAGEMENT
    # -------------------------------------------------------------------------
    def add_portfolio(self, name, capital, execution_mode):
        """Adds a new portfolio to the database."""
        print(f"🟢 Debug: Adding portfolio '{name}' with capital {capital} and mode '{execution_mode}'")
        self.cursor.execute('''
            INSERT INTO portfolios (name, capital, execution_mode)
            VALUES (?, ?, ?)
        ''', (name, capital, execution_mode))
        self.conn.commit()

        # Verify insertion
        self.cursor.execute("SELECT * FROM portfolios WHERE name = ?", (name,))
        added_portfolio = self.cursor.fetchone()
        print(f"✅ Debug: Portfolio added successfully: {added_portfolio}")

    def get_portfolios(self):
        """Retrieves all portfolios from the database."""
        self.cursor.execute('SELECT * FROM portfolios')
        portfolios = self.cursor.fetchall()
        print(f"📌 Debug: Retrieved portfolios: {portfolios}")
        return portfolios

    def delete_portfolio(self, portfolio_id):
        """Deletes a portfolio (but keeps stocks and strategies)."""
        print(f"🟢 Debug: Deleting portfolio with ID {portfolio_id}")
        self.cursor.execute('DELETE FROM portfolios WHERE id = ?', (portfolio_id,))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # STOCK MANAGEMENT (OLD "stocks" TABLE => NOW "portfolio_stocks")
    # We keep these methods for compatibility with existing code that expects:
    #    add_stock(portfolio_id, stock_ticker)
    #    get_stocks(portfolio_id=None)
    #    delete_stock(stock_id)
    # -------------------------------------------------------------------------
    def add_stock(self, portfolio_id, stock_ticker):
        """Adds a stock reference to a portfolio (legacy approach)."""
        print(f"🟢 Debug: Adding stock '{stock_ticker}' to portfolio ID {portfolio_id}")
        self.cursor.execute('''
            INSERT INTO portfolio_stocks (portfolio_id, stock_ticker)
            VALUES (?, ?)
        ''', (portfolio_id, stock_ticker))
        self.conn.commit()

    def get_stocks(self, portfolio_id=None):
        """
        Retrieves all stock references from 'portfolio_stocks',
        optionally filtered by portfolio_id.
        """
        if portfolio_id:
            print(f"📌 Debug: Getting stocks for portfolio ID {portfolio_id}")
            self.cursor.execute('''
                SELECT * FROM portfolio_stocks
                WHERE portfolio_id = ?
            ''', (portfolio_id,))
        else:
            print("📌 Debug: Getting all stocks (from portfolio_stocks).")
            self.cursor.execute('SELECT * FROM portfolio_stocks')
        stocks = self.cursor.fetchall()
        return stocks

    def delete_stock(self, stock_id):
        """Deletes a specific stock reference from 'portfolio_stocks' by its ID."""
        print(f"🟢 Debug: Deleting stock entry with ID {stock_id} from portfolio_stocks.")
        self.cursor.execute('''
            DELETE FROM portfolio_stocks
            WHERE id = ?
        ''', (stock_id,))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # MASTER STOCKS & FUNDAMENTALS
    # -------------------------------------------------------------------------
    def add_master_stock(self, ticker, company_name=None, sector=None):
        """
        Inserts a new row into the 'stocks' table for high-level stock info.
        If the ticker already exists, do nothing or update it.
        """
        print(f"🟢 Debug: Adding/Updating master stock info for '{ticker}'")
        try:
            # Attempt to insert new row
            self.cursor.execute('''
                INSERT INTO stocks (ticker, company_name, sector)
                VALUES (?, ?, ?)
            ''', (ticker, company_name, sector))
            self.conn.commit()
            print("✅ Debug: Master stock inserted successfully.")
        except sqlite3.IntegrityError:
            # Ticker already exists => optionally update
            print(f"🔄 Debug: Ticker '{ticker}' already exists, updating existing record.")
            self.cursor.execute('''
                UPDATE stocks
                SET company_name = COALESCE(?, company_name),
                    sector = COALESCE(?, sector)
                WHERE ticker = ?
            ''', (company_name, sector, ticker))
            self.conn.commit()

    def get_master_stock_tickers(self):
        """
        Retrieves all unique tickers from the stocks table, sorted alphabetically.
        """
        self.cursor.execute("SELECT ticker FROM stocks ORDER BY ticker ASC")
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def get_fundamental_columns(self):
        """
        Return a list of all column names (except 'id') in the 'fundamentals' table,
        based on the actual schema in SQLite.
        """
        self.cursor.execute("PRAGMA table_info(fundamentals)")
        rows = self.cursor.fetchall()  # row format: (cid, name, type, notnull, dflt_value, pk)
        columns = [r[1] for r in rows if r[1] != "id"]  # exclude primary key
        return columns

    def update_fundamentals(self,
        ticker,
        market_cap=None,
        pe_ratio=None,
        eps=None,
        dividend_yield=None,
        debt_to_equity=None,
        last_updated=None,
        forward_pe=None,
        price_to_book=None,
        price_to_sales=None,
        enterprise_to_ebitda=None,
        price_to_fcf=None,
        net_profit_margin=None,
        return_on_equity=None,
        return_on_assets=None,
        return_on_invested_capital=None,
        eps_growth=None,
        revenue_growth_yoy=None,
        earnings_growth_yoy=None,
        revenue_growth_3y=None,
        eps_growth_3y=None,
        dividend_payout_ratio=None,
        dividend_growth_5y=None,
        current_ratio=None,
        quick_ratio=None,
        interest_coverage=None,
        free_float=None,
        insider_ownership=None,
        institutional_ownership=None,
        beta=None,
        price_change_52w=None,
        # Extra fields from raw info:
        max_age=None,
        price_hint=None,
        previous_close=None,
        open_price=None,
        day_low=None,
        day_high=None,
        regular_market_previous_close=None,
        regular_market_open=None,
        regular_market_day_low=None,
        regular_market_day_high=None,
        regular_market_volume=None,
        average_volume=None,
        average_volume_10days=None,
        average_daily_volume_10day=None,
        bid=None,
        ask=None,
        bid_size=None,
        ask_size=None,
        fifty_two_week_low=None,
        fifty_two_week_high=None,
        fifty_day_average=None,
        two_hundred_day_average=None,
        trailing_annual_dividend_rate=None,
        trailing_annual_dividend_yield=None,
        currency=None,
        tradeable=None,
        quote_type=None,
        current_price=None,
        target_high_price=None,
        target_low_price=None,
        target_mean_price=None,
        target_median_price=None,
        recommendation_key=None,
        number_of_analyst_opinions=None,
        financial_currency=None,
        symbol=None,
        language=None,
        region=None,
        type_disp=None,
        quote_source_name=None,
        triggerable=None,
        custom_price_alert_confidence=None,
        market_state=None,
        long_name=None,
        regular_market_change_percent=None,
        short_name=None,
        regular_market_time=None,
        exchange=None,
        message_board_id=None,
        exchange_timezone_name=None,
        exchange_timezone_short_name=None,
        gmt_offset_milliseconds=None,
        market=None,
        esg_populated=None,
        corporate_actions=None,
        has_pre_post_market_data=None,
        first_trade_date_milliseconds=None,
        regular_market_change=None,
        regular_market_day_range=None,
        full_exchange_name=None,
        average_daily_volume_3month=None,
        fifty_two_week_low_change=None,
        fifty_two_week_low_change_percent=None,
        fifty_two_week_range=None,
        fifty_two_week_high_change=None,
        fifty_two_week_high_change_percent=None,
        fifty_two_week_change_percent=None,
        earnings_timestamp_start=None,
        earnings_timestamp_end=None,
        is_earnings_date_estimate=None,
        eps_trailing_twelve_months=None,
        eps_forward=None,
        eps_current_year=None,
        price_eps_current_year=None,
        shares_outstanding=None,
        book_value=None,
        fifty_day_average_change=None,
        fifty_day_average_change_percent=None,
        two_hundred_day_average_change=None,
        two_hundred_day_average_change_percent=None,
        source_interval=None,
        exchange_data_delayed_by=None,
        crypto_tradeable=None,
        trailing_peg_ratio=None,
        industry=None,
        sector=None
    ):
        """
        Inserts or updates fundamental data in the 'fundamentals' table.
        Exactly 115 placeholders for 115 columns (minus 'id').
        """
        # print(f"🟢 Debug: Updating fundamentals for '{ticker}' with extended metrics.")
        # print industry and sector
        print(f"🟢 Debug: Updating fundamentals for '{ticker}' with extended metrics. Industry: {industry}, Sector: {sector}")
        now_str = datetime.datetime.now().isoformat() if not last_updated else last_updated
        
        self.cursor.execute('SELECT id FROM fundamentals WHERE ticker = ?', (ticker,))
        existing = self.cursor.fetchone()
        
        if existing:
            # ---------------------------------------
            # UPDATE: 115 placeholders, 1 for 'ticker' at the end
            # ---------------------------------------
            self.cursor.execute('''
                UPDATE fundamentals
                SET
                    market_cap = COALESCE(?, market_cap),
                    pe_ratio = COALESCE(?, pe_ratio),
                    eps = COALESCE(?, eps),
                    dividend_yield = COALESCE(?, dividend_yield),
                    debt_to_equity = COALESCE(?, debt_to_equity),
                    last_updated = ?,
                    forward_pe = COALESCE(?, forward_pe),
                    price_to_book = COALESCE(?, price_to_book),
                    price_to_sales = COALESCE(?, price_to_sales),
                    enterprise_to_ebitda = COALESCE(?, enterprise_to_ebitda),
                    price_to_fcf = COALESCE(?, price_to_fcf),
                    net_profit_margin = COALESCE(?, net_profit_margin),
                    return_on_equity = COALESCE(?, return_on_equity),
                    return_on_assets = COALESCE(?, return_on_assets),
                    return_on_invested_capital = COALESCE(?, return_on_invested_capital),
                    eps_growth = COALESCE(?, eps_growth),
                    revenue_growth_yoy = COALESCE(?, revenue_growth_yoy),
                    earnings_growth_yoy = COALESCE(?, earnings_growth_yoy),
                    revenue_growth_3y = COALESCE(?, revenue_growth_3y),
                    eps_growth_3y = COALESCE(?, eps_growth_3y),
                    dividend_payout_ratio = COALESCE(?, dividend_payout_ratio),
                    dividend_growth_5y = COALESCE(?, dividend_growth_5y),
                    current_ratio = COALESCE(?, current_ratio),
                    quick_ratio = COALESCE(?, quick_ratio),
                    interest_coverage = COALESCE(?, interest_coverage),
                    free_float = COALESCE(?, free_float),
                    insider_ownership = COALESCE(?, insider_ownership),
                    institutional_ownership = COALESCE(?, institutional_ownership),
                    beta = COALESCE(?, beta),
                    price_change_52w = COALESCE(?, price_change_52w),
                    
                    max_age = COALESCE(?, max_age),
                    price_hint = COALESCE(?, price_hint),
                    previous_close = COALESCE(?, previous_close),
                    open_price = COALESCE(?, open_price),
                    day_low = COALESCE(?, day_low),
                    day_high = COALESCE(?, day_high),
                    regular_market_previous_close = COALESCE(?, regular_market_previous_close),
                    regular_market_open = COALESCE(?, regular_market_open),
                    regular_market_day_low = COALESCE(?, regular_market_day_low),
                    regular_market_day_high = COALESCE(?, regular_market_day_high),
                    regular_market_volume = COALESCE(?, regular_market_volume),
                    average_volume = COALESCE(?, average_volume),
                    average_volume_10days = COALESCE(?, average_volume_10days),
                    average_daily_volume_10day = COALESCE(?, average_daily_volume_10day),
                    bid = COALESCE(?, bid),
                    ask = COALESCE(?, ask),
                    bid_size = COALESCE(?, bid_size),
                    ask_size = COALESCE(?, ask_size),
                    fifty_two_week_low = COALESCE(?, fifty_two_week_low),
                    fifty_two_week_high = COALESCE(?, fifty_two_week_high),
                    fifty_day_average = COALESCE(?, fifty_day_average),
                    two_hundred_day_average = COALESCE(?, two_hundred_day_average),
                    trailing_annual_dividend_rate = COALESCE(?, trailing_annual_dividend_rate),
                    trailing_annual_dividend_yield = COALESCE(?, trailing_annual_dividend_yield),
                    currency = COALESCE(?, currency),
                    tradeable = COALESCE(?, tradeable),
                    quote_type = COALESCE(?, quote_type),
                    current_price = COALESCE(?, current_price),
                    target_high_price = COALESCE(?, target_high_price),
                    target_low_price = COALESCE(?, target_low_price),
                    target_mean_price = COALESCE(?, target_mean_price),
                    target_median_price = COALESCE(?, target_median_price),
                    recommendation_key = COALESCE(?, recommendation_key),
                    number_of_analyst_opinions = COALESCE(?, number_of_analyst_opinions),
                    financial_currency = COALESCE(?, financial_currency),
                    symbol = COALESCE(?, symbol),
                    language = COALESCE(?, language),
                    region = COALESCE(?, region),
                    type_disp = COALESCE(?, type_disp),
                    quote_source_name = COALESCE(?, quote_source_name),
                    triggerable = COALESCE(?, triggerable),
                    custom_price_alert_confidence = COALESCE(?, custom_price_alert_confidence),
                    market_state = COALESCE(?, market_state),
                    long_name = COALESCE(?, long_name),
                    regular_market_change_percent = COALESCE(?, regular_market_change_percent),
                    short_name = COALESCE(?, short_name),
                    regular_market_time = COALESCE(?, regular_market_time),
                    exchange = COALESCE(?, exchange),
                    message_board_id = COALESCE(?, message_board_id),
                    exchange_timezone_name = COALESCE(?, exchange_timezone_name),
                    exchange_timezone_short_name = COALESCE(?, exchange_timezone_short_name),
                    gmt_offset_milliseconds = COALESCE(?, gmt_offset_milliseconds),
                    market = COALESCE(?, market),
                    esg_populated = COALESCE(?, esg_populated),
                    corporate_actions = COALESCE(?, corporate_actions),
                    has_pre_post_market_data = COALESCE(?, has_pre_post_market_data),
                    first_trade_date_milliseconds = COALESCE(?, first_trade_date_milliseconds),
                    regular_market_change = COALESCE(?, regular_market_change),
                    regular_market_day_range = COALESCE(?, regular_market_day_range),
                    full_exchange_name = COALESCE(?, full_exchange_name),
                    average_daily_volume_3month = COALESCE(?, average_daily_volume_3month),
                    fifty_two_week_low_change = COALESCE(?, fifty_two_week_low_change),
                    fifty_two_week_low_change_percent = COALESCE(?, fifty_two_week_low_change_percent),
                    fifty_two_week_range = COALESCE(?, fifty_two_week_range),
                    fifty_two_week_high_change = COALESCE(?, fifty_two_week_high_change),
                    fifty_two_week_high_change_percent = COALESCE(?, fifty_two_week_high_change_percent),
                    fifty_two_week_change_percent = COALESCE(?, fifty_two_week_change_percent),
                    earnings_timestamp_start = COALESCE(?, earnings_timestamp_start),
                    earnings_timestamp_end = COALESCE(?, earnings_timestamp_end),
                    is_earnings_date_estimate = COALESCE(?, is_earnings_date_estimate),
                    eps_trailing_twelve_months = COALESCE(?, eps_trailing_twelve_months),
                    eps_forward = COALESCE(?, eps_forward),
                    eps_current_year = COALESCE(?, eps_current_year),
                    price_eps_current_year = COALESCE(?, price_eps_current_year),
                    shares_outstanding = COALESCE(?, shares_outstanding),
                    book_value = COALESCE(?, book_value),
                    fifty_day_average_change = COALESCE(?, fifty_day_average_change),
                    fifty_day_average_change_percent = COALESCE(?, fifty_day_average_change_percent),
                    two_hundred_day_average_change = COALESCE(?, two_hundred_day_average_change),
                    two_hundred_day_average_change_percent = COALESCE(?, two_hundred_day_average_change_percent),
                    source_interval = COALESCE(?, source_interval),
                    exchange_data_delayed_by = COALESCE(?, exchange_data_delayed_by),
                    crypto_tradeable = COALESCE(?, crypto_tradeable),
                    trailing_peg_ratio = COALESCE(?, trailing_peg_ratio),
                    industry = COALESCE(?, industry),
                    sector = COALESCE(?, sector)            
                WHERE ticker = ?
            ''', (
                market_cap, pe_ratio, eps, dividend_yield, debt_to_equity,
                now_str,
                forward_pe, price_to_book, price_to_sales, enterprise_to_ebitda, price_to_fcf,
                net_profit_margin, return_on_equity, return_on_assets, return_on_invested_capital,
                eps_growth, revenue_growth_yoy, earnings_growth_yoy, revenue_growth_3y, eps_growth_3y,
                dividend_payout_ratio, dividend_growth_5y, current_ratio, quick_ratio, interest_coverage,
                free_float, insider_ownership, institutional_ownership, beta, price_change_52w,
                max_age, price_hint, previous_close, open_price, day_low, day_high,
                regular_market_previous_close, regular_market_open, regular_market_day_low, regular_market_day_high,
                regular_market_volume, average_volume, average_volume_10days, average_daily_volume_10day,
                bid, ask, bid_size, ask_size,
                fifty_two_week_low, fifty_two_week_high, fifty_day_average, two_hundred_day_average,
                trailing_annual_dividend_rate, trailing_annual_dividend_yield, currency, tradeable,
                quote_type, current_price, target_high_price, target_low_price, target_mean_price, target_median_price,
                recommendation_key, number_of_analyst_opinions, financial_currency, symbol, language, region,
                type_disp, quote_source_name, triggerable, custom_price_alert_confidence, market_state,
                long_name, regular_market_change_percent, short_name, regular_market_time, exchange, message_board_id,
                exchange_timezone_name, exchange_timezone_short_name, gmt_offset_milliseconds, market, esg_populated,
                corporate_actions, has_pre_post_market_data, first_trade_date_milliseconds, regular_market_change,
                regular_market_day_range, full_exchange_name, average_daily_volume_3month, fifty_two_week_low_change,
                fifty_two_week_low_change_percent, fifty_two_week_range, fifty_two_week_high_change,
                fifty_two_week_high_change_percent, fifty_two_week_change_percent, earnings_timestamp_start,
                earnings_timestamp_end, is_earnings_date_estimate, eps_trailing_twelve_months, eps_forward,
                eps_current_year, price_eps_current_year, shares_outstanding, book_value, fifty_day_average_change,
                fifty_day_average_change_percent, two_hundred_day_average_change, two_hundred_day_average_change_percent,
                source_interval, exchange_data_delayed_by, crypto_tradeable, trailing_peg_ratio, industry, sector,
                ticker
            ))
            print("✅ Debug: Fundamentals updated.")
        else:
            # ---------------------------------------
            # INSERT: 115 columns => 115 placeholders
            # ---------------------------------------
            self.cursor.execute('''
                INSERT INTO fundamentals (
                    ticker, market_cap, pe_ratio, eps, dividend_yield, debt_to_equity, last_updated,
                    forward_pe, price_to_book, price_to_sales, enterprise_to_ebitda, price_to_fcf,
                    net_profit_margin, return_on_equity, return_on_assets, return_on_invested_capital,
                    eps_growth, revenue_growth_yoy, earnings_growth_yoy, revenue_growth_3y, eps_growth_3y,
                    dividend_payout_ratio, dividend_growth_5y, current_ratio, quick_ratio, interest_coverage,
                    free_float, insider_ownership, institutional_ownership, beta, price_change_52w,
                    max_age, price_hint, previous_close, open_price, day_low, day_high,
                    regular_market_previous_close, regular_market_open, regular_market_day_low, regular_market_day_high,
                    regular_market_volume, average_volume, average_volume_10days, average_daily_volume_10day,
                    bid, ask, bid_size, ask_size,
                    fifty_two_week_low, fifty_two_week_high, fifty_day_average, two_hundred_day_average,
                    trailing_annual_dividend_rate, trailing_annual_dividend_yield, currency, tradeable,
                    quote_type, current_price, target_high_price, target_low_price, target_mean_price, target_median_price,
                    recommendation_key, number_of_analyst_opinions, financial_currency, symbol, language, region,
                    type_disp, quote_source_name, triggerable, custom_price_alert_confidence, market_state,
                    long_name, regular_market_change_percent, short_name, regular_market_time, exchange, message_board_id,
                    exchange_timezone_name, exchange_timezone_short_name, gmt_offset_milliseconds, market, esg_populated,
                    corporate_actions, has_pre_post_market_data, first_trade_date_milliseconds, regular_market_change,
                    regular_market_day_range, full_exchange_name, average_daily_volume_3month, fifty_two_week_low_change,
                    fifty_two_week_low_change_percent, fifty_two_week_range, fifty_two_week_high_change,
                    fifty_two_week_high_change_percent, fifty_two_week_change_percent, earnings_timestamp_start,
                    earnings_timestamp_end, is_earnings_date_estimate, eps_trailing_twelve_months, eps_forward,
                    eps_current_year, price_eps_current_year, shares_outstanding, book_value, fifty_day_average_change,
                    fifty_day_average_change_percent, two_hundred_day_average_change, two_hundred_day_average_change_percent,
                    source_interval, exchange_data_delayed_by, crypto_tradeable, trailing_peg_ratio, industry, sector
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?
                )
            ''', (
                ticker, market_cap, pe_ratio, eps, dividend_yield, debt_to_equity,
                now_str,
                forward_pe, price_to_book, price_to_sales, enterprise_to_ebitda, price_to_fcf,
                net_profit_margin, return_on_equity, return_on_assets, return_on_invested_capital,
                eps_growth, revenue_growth_yoy, earnings_growth_yoy, revenue_growth_3y, eps_growth_3y,
                dividend_payout_ratio, dividend_growth_5y, current_ratio, quick_ratio, interest_coverage,
                free_float, insider_ownership, institutional_ownership, beta, price_change_52w,
                max_age, price_hint, previous_close, open_price, day_low, day_high,
                regular_market_previous_close, regular_market_open, regular_market_day_low, regular_market_day_high,
                regular_market_volume, average_volume, average_volume_10days, average_daily_volume_10day,
                bid, ask, bid_size, ask_size,
                fifty_two_week_low, fifty_two_week_high, fifty_day_average, two_hundred_day_average,
                trailing_annual_dividend_rate, trailing_annual_dividend_yield, currency, tradeable,
                quote_type, current_price, target_high_price, target_low_price, target_mean_price, target_median_price,
                recommendation_key, number_of_analyst_opinions, financial_currency, symbol, language, region,
                type_disp, quote_source_name, triggerable, custom_price_alert_confidence, market_state,
                long_name, regular_market_change_percent, short_name, regular_market_time, exchange, message_board_id,
                exchange_timezone_name, exchange_timezone_short_name, gmt_offset_milliseconds, market, esg_populated,
                corporate_actions, has_pre_post_market_data, first_trade_date_milliseconds, regular_market_change,
                regular_market_day_range, full_exchange_name, average_daily_volume_3month, fifty_two_week_low_change,
                fifty_two_week_low_change_percent, fifty_two_week_range, fifty_two_week_high_change,
                fifty_two_week_high_change_percent, fifty_two_week_change_percent, earnings_timestamp_start,
                earnings_timestamp_end, is_earnings_date_estimate, eps_trailing_twelve_months, eps_forward,
                eps_current_year, price_eps_current_year, shares_outstanding, book_value, fifty_day_average_change,
                fifty_day_average_change_percent, two_hundred_day_average_change, two_hundred_day_average_change_percent,
                source_interval, exchange_data_delayed_by, crypto_tradeable, trailing_peg_ratio, industry, sector
                
            ))
            print("✅ Debug: Fundamentals inserted.")
        self.conn.commit()

        
    def get_fundamentals(self, ticker):
        """
        Retrieves fundamental data for a given ticker.
        """
        print(f"📌 Debug: Getting fundamentals for '{ticker}'")
        self.cursor.execute('SELECT * FROM fundamentals WHERE ticker = ?', (ticker,))
        return self.cursor.fetchone()

    def get_fundamental_value(self, ticker: str, field_name: str):
        valid_columns = self.get_fundamental_columns()
        if field_name not in valid_columns:
            print(f"[WARNING] Requested field '{field_name}' is not in fundamentals.")
            return None

        query = f"SELECT {field_name} FROM fundamentals WHERE ticker = ?"
        self.cursor.execute(query, (ticker,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def get_fundamentals_last_updated(self, ticker):
        """
        Returns the last_updated string from fundamentals for the given ticker,
        or None if not found.
        """
        self.cursor.execute('''
            SELECT last_updated
            FROM fundamentals
            WHERE ticker = ?
        ''', (ticker,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    # -------------------------------------------------------------------------
    # HISTORICAL PRICE MANAGEMENT
    # -------------------------------------------------------------------------
    def store_price_data(self, ticker, price_rows):
        """
        Inserts or updates daily price data in 'historical_prices' for a given ticker.
        price_rows should be a list of dicts or tuples with columns:
            date, open_price, high_price, low_price, close_price, adjusted_close, volume
        """
        print(f"🟢 Debug: Storing price data for '{ticker}'")
        for row in price_rows:
            # Check if (ticker, date) already exists
            self.cursor.execute('''
                SELECT id
                FROM historical_prices
                WHERE ticker = ? AND date = ?
            ''', (ticker, row["date"]))
            existing = self.cursor.fetchone()

            if existing:
                # Update
                self.cursor.execute('''
                    UPDATE historical_prices
                    SET open_price = ?,
                        high_price = ?,
                        low_price = ?,
                        close_price = ?,
                        adjusted_close = ?,
                        volume = ?
                    WHERE id = ?
                ''', (
                    row["open_price"], row["high_price"], row["low_price"],
                    row["close_price"], row["adjusted_close"], row["volume"],
                    existing[0]
                ))
            else:
                # Insert
                self.cursor.execute('''
                    INSERT INTO historical_prices (
                        ticker, date, open_price, high_price,
                        low_price, close_price, adjusted_close, volume
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ticker, row["date"], row["open_price"], row["high_price"],
                    row["low_price"], row["close_price"], row["adjusted_close"],
                    row["volume"]
                ))
        self.conn.commit()
        print("✅ Debug: Price data stored/updated successfully.")

    def get_price_data(self, ticker, start_date=None, end_date=None):
        """
        Retrieves historical price data for a given ticker, optionally between date ranges.
        Returns a list of rows.
        """
        print(f"📌 Debug: Getting price data for '{ticker}' from {start_date} to {end_date}")
        query = '''
            SELECT date, open_price, high_price, low_price, close_price, adjusted_close, volume
            FROM historical_prices
            WHERE ticker = ?
        '''
        params = [ticker]

        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)

        query += ' ORDER BY date ASC'
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return rows

    # -------------------------------------------------------------------------
    # STRATEGY MANAGEMENT (Existing Code)
    # -------------------------------------------------------------------------
    def add_strategy(self, strategy_name, parameters, portfolio_ids):
        """Adds a strategy and links it to multiple portfolios."""
        print(f"🟢 Debug: Attempting to add strategy '{strategy_name}' for portfolios {portfolio_ids}")

        # Store the strategy once
        self.cursor.execute('''
            INSERT INTO strategies (strategy_name, parameters)
            VALUES (?, ?)
        ''', (strategy_name, json.dumps(parameters)))
        strategy_id = self.cursor.lastrowid
        print(f"✅ Debug: Strategy successfully inserted with ID {strategy_id}")

        # Link strategy to each portfolio
        for pid in portfolio_ids:
            print(f"🔗 Debug: Linking strategy ID {strategy_id} to portfolio ID {pid}")
            self.cursor.execute('''
                INSERT INTO portfolio_strategies (portfolio_id, strategy_id)
                VALUES (?, ?)
            ''', (pid, strategy_id))

        self.conn.commit()
        print(f"✅ Debug: Strategy '{strategy_name}' successfully linked to portfolios.")

    def get_strategies(self, portfolio_id=None):
        """Retrieves strategies, optionally filtered by portfolio_id."""
        if portfolio_id is not None:
            self.cursor.execute('''
                SELECT s.id, s.strategy_name, s.parameters
                FROM strategies AS s
                JOIN portfolio_strategies AS ps ON s.id = ps.strategy_id
                WHERE ps.portfolio_id = ?
            ''', (portfolio_id,))
        else:
            self.cursor.execute('SELECT id, strategy_name, parameters FROM strategies')

        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'name': row[1],
                'parameters': json.loads(row[2])
            })
        print(f"📌 Debug: Retrieved strategies (portfolio_id={portfolio_id}): {results}")
        return results

    def get_portfolio_strategies(self, portfolio_id):
        """Retrieves strategies linked to a given portfolio."""
        print(f"🔍 Fetching strategies for portfolio ID: {portfolio_id}")
        self.cursor.execute('''
            SELECT s.id, s.strategy_name, s.parameters
            FROM strategies s
            INNER JOIN portfolio_strategies ps ON s.id = ps.strategy_id
            WHERE ps.portfolio_id = ?
        ''', (portfolio_id,))
        strategies = self.cursor.fetchall()
        print(f"📌 Retrieved strategies for portfolio ID {portfolio_id}: {[s[1] for s in strategies]}")
        return [{
            "id": s[0],
            "name": s[1],
            "parameters": json.loads(s[2])
        } for s in strategies]

    def update_strategy(self, strategy_id, new_parameters):
        """Updates a strategy's parameters."""
        self.cursor.execute('''
            UPDATE strategies
            SET parameters = ?
            WHERE id = ?
        ''', (json.dumps(new_parameters), strategy_id))
        self.conn.commit()
        print(f"Updated strategy ID {strategy_id} with new parameters.")

    def delete_strategy(self, strategy_id):
        """Deletes a specific strategy."""
        print(f"🟢 Debug: Deleting strategy ID {strategy_id}")
        self.cursor.execute('DELETE FROM strategies WHERE id = ?', (strategy_id,))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # TRADES & PORTFOLIO VALUE
    # -------------------------------------------------------------------------
    def add_trade(self, portfolio_id, stock_ticker, trade_type, quantity, price, transaction_cost=0.0):
        """Logs a trade with price, quantity, and transaction cost."""
        print(f"🟢 Debug: Adding trade: {trade_type} {quantity} shares of {stock_ticker} at {price}, cost={transaction_cost}")
        self.cursor.execute('''
            INSERT INTO trades (portfolio_id, stock_ticker, trade_type, quantity, price, transaction_cost)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (portfolio_id, stock_ticker, trade_type, quantity, price, transaction_cost))
        self.conn.commit()

    def get_trades(self, portfolio_id=None):
        """Retrieves trades, optionally filtered by portfolio."""
        if portfolio_id:
            print(f"📌 Debug: Getting trades for portfolio ID {portfolio_id}")
            self.cursor.execute('''
                SELECT * FROM trades
                WHERE portfolio_id = ?
            ''', (portfolio_id,))
        else:
            print("📌 Debug: Getting all trades.")
            self.cursor.execute('SELECT * FROM trades')
        return self.cursor.fetchall()

    def delete_trade(self, trade_id):
        """Deletes a specific trade."""
        print(f"🟢 Debug: Deleting trade ID {trade_id}")
        self.cursor.execute('DELETE FROM trades WHERE id = ?', (trade_id,))
        self.conn.commit()

    def calculate_portfolio_value(self, portfolio_id):
        """Calculates the portfolio's total value based on executed trades."""
        print(f"📌 Debug: Calculating portfolio value for ID {portfolio_id}")
        self.cursor.execute('''
            SELECT trade_type, quantity, price, transaction_cost
            FROM trades
            WHERE portfolio_id = ?
        ''', (portfolio_id,))
        trades = self.cursor.fetchall()

        total_value = 0
        for trade_type, quantity, price, transaction_cost in trades:
            if trade_type == 'buy':
                total_value -= (quantity * price) + transaction_cost
            elif trade_type == 'sell':
                total_value += (quantity * price) - transaction_cost

        return total_value

    # -------------------------------------------------------------------------
    # STOCK SCREENING
    # -------------------------------------------------------------------------
    def add_stock_screen(self, name, criteria, stock_limit=None):
        """Adds a new stock screen with filtering criteria stored as JSON."""
        self.cursor.execute('''
            INSERT INTO stock_screens (name, criteria, stock_limit) 
            VALUES (?, ?, ?)
        ''', (name, json.dumps(criteria), stock_limit))
        self.conn.commit()

    def get_stock_screens(self):
        """Fetches all saved stock screens."""
        self.cursor.execute('SELECT id, name, criteria, stock_limit, created_at FROM stock_screens')
        screens = self.cursor.fetchall()
        return [
            {"id": s[0], "name": s[1], "criteria": json.loads(s[2]), "stock_limit": s[3], "created_at": s[4]}
            for s in screens
        ]

    def update_stock_screen(self, screen_id, name, criteria, stock_limit):
        """Updates an existing stock screen."""
        self.cursor.execute('''
            UPDATE stock_screens 
            SET name = ?, criteria = ?, stock_limit = ? 
            WHERE id = ?
        ''', (name, json.dumps(criteria), stock_limit, screen_id))
        self.conn.commit()

    def delete_stock_screen(self, screen_id):
            """Deletes a stock screen by ID."""
            self.cursor.execute('DELETE FROM stock_screens WHERE id = ?', (screen_id,))
            self.conn.commit()

    # -------------------------------------------------------------------------
    # Linking Portfolios to Stock Screens
    # -------------------------------------------------------------------------
    def link_screen_to_portfolio(self, portfolio_id, screen_id):
        """Links a stock screen to a portfolio."""
        self.cursor.execute('''
            INSERT INTO portfolio_screens (portfolio_id, screen_id) 
            VALUES (?, ?)
        ''', (portfolio_id, screen_id))
        self.conn.commit()

    def get_screens_for_portfolio(self, portfolio_id):
        """Fetches all stock screens associated with a given portfolio."""
        self.cursor.execute('''
            SELECT stock_screens.id, stock_screens.name, stock_screens.criteria, stock_screens.stock_limit
            FROM stock_screens
            JOIN portfolio_screens ON stock_screens.id = portfolio_screens.screen_id
            WHERE portfolio_screens.portfolio_id = ?
        ''', (portfolio_id,))
        
        screens = self.cursor.fetchall()
        return [{"id": s[0], "name": s[1], "criteria": json.loads(s[2]), "stock_limit": s[3]} for s in screens]
    
    def unlink_screen_from_portfolio(self, portfolio_id, screen_id):
        """Removes a stock screen from a portfolio."""
        self.cursor.execute('''
            DELETE FROM portfolio_screens WHERE portfolio_id = ? AND screen_id = ?
        ''', (portfolio_id, screen_id))
        self.conn.commit()

    def apply_stock_screen(self, screen_id):
        """
        Dynamically build a filter query using only columns that 
        actually exist and are numeric in `fundamentals`.
        """

        # 1) Get the screen's criteria
        self.cursor.execute('SELECT criteria, stock_limit FROM stock_screens WHERE id = ?', (screen_id,))
        row = self.cursor.fetchone()
        if not row:
            return {"results": [], "ignored_filters": []}

        import json
        criteria_json, stock_limit = row
        try:
            criteria = json.loads(criteria_json)
        except json.JSONDecodeError:
            return {"results": [], "ignored_filters": []}

        # 2) Fetch numeric columns from `fundamentals`
        numeric_cols = self.get_numeric_columns_for_fundamentals()

        # 3) Build the SELECT query (you can do SELECT * if you want everything)
        query = "SELECT * FROM fundamentals WHERE 1=1"
        params = []
        ignored = []

        # 4) For each criterion in user’s JSON, check if column exists in numeric_cols
        for col, condition in criteria.items():
            if col not in numeric_cols:
                ignored.append(col)
                continue
            # If condition is e.g. {"min": 5, "max": 20}
            # We'll handle min <= col <= max
            if not isinstance(condition, dict):
                # If user just said "col": 15, decide how to interpret or ignore
                ignored.append(col)
                continue

            # "min" => col >= ?
            if "min" in condition:
                query += f" AND {col} >= ?"
                params.append(condition["min"])

            # "max" => col <= ?
            if "max" in condition:
                query += f" AND {col} <= ?"
                params.append(condition["max"])

        # 5) Sort by market_cap descending or something else
        query += " ORDER BY market_cap DESC"

        # 6) If user specified stock_limit
        if stock_limit:
            query += f" LIMIT {stock_limit}"

        # 7) Run the query
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()

        # 8) We can gather column names from the cursor description
        col_names = [desc[0] for desc in self.cursor.description]

        # Build results
        final = []
        for row_data in rows:
            row_dict = dict(zip(col_names, row_data))
            final.append(row_dict)

        return {"results": final, "ignored_filters": ignored}

    def assign_strategy_to_portfolios(self, strategy_id, portfolio_ids):
        """Assigns an existing strategy to a set of portfolios."""
        # First remove old links
        self.cursor.execute('DELETE FROM portfolio_strategies WHERE strategy_id = ?', (strategy_id,))
        # Insert new links
        for pid in portfolio_ids:
            self.cursor.execute('INSERT INTO portfolio_strategies (portfolio_id, strategy_id) VALUES (?, ?)', (pid, strategy_id))
        self.conn.commit()

    def get_numeric_columns_for_fundamentals(self):
        """
        Returns a set of column names in `fundamentals` that
        are numeric (REAL, INT, etc.) so we can do min/max filters.
        """
        self.cursor.execute("PRAGMA table_info(fundamentals)")
        columns = self.cursor.fetchall()
        numeric_cols = set()
        for col in columns:
            col_name = col[1]  # the 'name' field
            col_type = col[2].upper()  # the 'type' field, e.g. 'REAL', 'TEXT'
            if col_type in ("REAL", "INTEGER", "INT", "FLOAT", "DOUBLE"):
                numeric_cols.add(col_name)
        return numeric_cols


    # -------------------------------------------------------------------------
    # DATABASE MAINTENANCE
    # -------------------------------------------------------------------------
    def clean_database(self):
        """
        Removes orphaned records from the database.
        For example, portfolio_stocks where portfolio_id or stock_ticker doesn't exist.
        Also cleans up strategy links if needed.
        """
        print("🟢 Debug: Cleaning database - Removing orphaned records.")
        try:
            # Remove portfolio_stocks whose portfolio_id no longer exists
            self.cursor.execute('''
                DELETE FROM portfolio_stocks
                WHERE portfolio_id NOT IN (SELECT id FROM portfolios)
            ''')
            # Potentially remove portfolio_stocks whose ticker isn't in 'stocks' table
            self.cursor.execute('''
                DELETE FROM portfolio_stocks
                WHERE stock_ticker NOT IN (SELECT ticker FROM stocks)
            ''')

            # Remove strategy links if portfolio or strategy no longer exists
            self.cursor.execute('''
                DELETE FROM portfolio_strategies
                WHERE portfolio_id NOT IN (SELECT id FROM portfolios)
                   OR strategy_id NOT IN (SELECT id FROM strategies)
            ''')

            # Remove orphaned strategies (not linked to any portfolio)
            self.cursor.execute('''
                DELETE FROM strategies
                WHERE id NOT IN (
                    SELECT strategy_id FROM portfolio_strategies)
            ''')

            self.conn.commit()
            print("✅ Debug: Database cleanup completed successfully.")

        except sqlite3.OperationalError as e:
            print(f"❌ SQLite Error during cleanup: {e}")

    def get_price_dataframe(self, ticker, start_date=None, end_date=None):
        """
        Retrieves historical price data from the database and returns
        a Pandas DataFrame suitable for a Backtrader feed.
        The DataFrame will contain columns:
        ['datetime', 'open', 'high', 'low', 'close', 'volume', 'openinterest'].

        :param ticker: The stock ticker to query.
        :param start_date: Optional filter for rows (YYYY-MM-DD).
        :param end_date: Optional filter for rows (YYYY-MM-DD).
        :return: A Pandas DataFrame ready for backtrader.
        """
        # 1) Grab the raw rows from the historical_prices table
        rows = self.get_price_data(ticker, start_date, end_date)  # existing method

        # rows will be a list of tuples => (date, open_price, high_price, ...)
        # Typically: [(2020-01-01, 100, 110, 99, 105, 104, 1000000), ...]

        # 2) Convert rows into a DataFrame
        columns = ["date", "open_price", "high_price", "low_price",
                "close_price", "adjusted_close", "volume"]
        df = pd.DataFrame(rows, columns=columns)

        if df.empty:
            # Return empty or raise an exception if no data found
            return pd.DataFrame()

        # 3) Convert "date" column to datetime
        df["date"] = pd.to_datetime(df["date"])

        # 4) Rename columns to the format that Backtrader expects:
        #    'open', 'high', 'low', 'close', 'volume', 'openinterest'
        df.rename(
            columns={
                "open_price": "open",
                "high_price": "high",
                "low_price": "low",
                # "close_price": "close",
            },
            inplace=True
        )

        # optional: if you want 'adjusted_close' to be used as 'close', you can do:
        df["close"] = df["adjusted_close"]

        # 5) Add a placeholder column for open interest (required by Backtrader)
        df["openinterest"] = 0.0

        # 6) Set the 'date' column as the DataFrame index
        df.set_index("date", inplace=True)

        # 7) Ensure rows are sorted by date
        df.sort_index(inplace=True)

        return df

    def close_connection(self):
        """Closes the database connection."""
        self.conn.close()

# If run directly, create tables and show debug info
if __name__ == "__main__":
    db = TradingDatabase()
    print("✅ Database initialized successfully.")
    db.close_connection()
