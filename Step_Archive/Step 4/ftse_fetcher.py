# ftse_fetcher.py

import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO

class FTSETickerFetcher:
    """
    A simple class to scrape Wikipedia pages for various FTSE indexes
    and return a dynamic list of tickers (e.g., adding '.L' if needed).
    No logic about fundamental data or skipping fresh updates.
    """

    def __init__(self):
        """
        You can remove or rename 'db' if no longer needed. 
        This class just focuses on scraping tickers.
        """
        self.INDEX_URLS = {
            "FTSE 100": "https://en.wikipedia.org/wiki/FTSE_100_Index",
            "FTSE 250": "https://en.wikipedia.org/wiki/FTSE_250_Index",
            #"FTSE 350": "https://en.wikipedia.org/wiki/FTSE_350_Index",
            #"FTSE SmallCap": "https://en.wikipedia.org/wiki/FTSE_SmallCap_Index",
            #"FTSE All-Share": "https://en.wikipedia.org/wiki/FTSE_All-Share_Index",
            #"FTSE Fledgling": "https://en.wikipedia.org/wiki/FTSE_Fledgling_Index",
            #"FTSE AIM UK 50": "https://en.wikipedia.org/wiki/FTSE_AIM_UK_50_Index"
        }

    def get_all_ftse_index_tickers(self) -> dict:
        """
        Scrapes each FTSE index page in self.INDEX_URLS, returning
        a dict of { index_name: [list_of_tickers], ... }.
        """
        all_index_tickers = {}
        for index_name, url in self.INDEX_URLS.items():
            print(f"\n=== Retrieving {index_name} from {url} ===")
            raw_tickers = self._get_tickers_from_wikipedia(url)
            all_index_tickers[index_name] = raw_tickers
            print(f"Found {len(raw_tickers)} total for {index_name}")
        return all_index_tickers

    def _get_tickers_from_wikipedia(self, url: str) -> list:
        """
        Internal method that scrapes the Wikipedia page at `url`,
        finds 'wikitable sortable' tables, and extracts possible Ticker columns.
        Returns a list of cleaned ticker strings (e.g., appending '.L' if needed).
        """
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Wikipedia often uses 'wikitable sortable' for constituents
        tables = soup.find_all("table", {"class": "wikitable sortable"})
        if not tables:
            print("No 'wikitable sortable' tables found on this page.")
            return []

        collected_tickers = []
        for idx, table in enumerate(tables):
            df_list = pd.read_html(StringIO(str(table)))
            if not df_list:
                continue

            df = df_list[0]
            print(f"\n--- Analyzing table #{idx+1} with columns: {df.columns} ---")

            # Potential columns containing ticker data
            potential_cols = [
                c for c in df.columns 
                if any(keyword in str(c) for keyword in ["EPIC", "Ticker", "Symbol"])
            ]
            if not potential_cols:
                print("No Ticker/EPIC column found in this table.")
                continue

            # Use the first matching column
            col = potential_cols[0]
            df.rename(columns={col: "Ticker"}, inplace=True)
            tickers_raw = df["Ticker"].dropna().tolist()

            for t in tickers_raw:
                t_str = str(t).split('[')[0].strip()  # remove footnotes like [1]
                # If short and missing .L, add .L
                if not t_str.endswith(".L") and len(t_str) <= 5:
                    t_str += ".L"
                collected_tickers.append(t_str)

        return list(set(collected_tickers))  # unique
