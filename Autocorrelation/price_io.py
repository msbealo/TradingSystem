# """io.py
# ~~~~~~~~
# Utilities for loading and trimming price–time‑series data so that the rest of the
# Ehlers toolkit can work on a clean, NumPy‑friendly representation.

# The guiding idea is to *always* load **slightly more data than you intend to
# plot/trade**, so that indicators with internal state (e.g. moving averages,
# filters, autocorrelation) have time to warm‑up before the visible window.

# Functions
# ---------
# load_prices
#     Read a CSV, convert dates, apply an optional warm‑up extension on the
#     left‑hand side, and return `numpy.ndarray` objects that can be sliced
#     quickly in downstream code.

# Example
# -------
# >>> from io import load_prices
# >>> dates, prices = load_prices(
# ...     path="Gold-10years.csv",
# ...     start="2024-07-01",
# ...     end="2025-07-03",
# ...     warmup=52)        # 48‑bar max‑lag + 4‑bar centring shift
# """
from __future__ import annotations

import pathlib
from typing import Tuple, Union

import numpy as np
import pandas as pd

DateLike = Union[str, "pd.Timestamp", np.datetime64]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_prices(
    path: Union[str, pathlib.Path],
    start: DateLike,
    end: DateLike,
    warmup: int = 0,
    *,
    date_col: str = "Date",
    value_col: str = "Value",
    date_format: str | None = "%m/%d/%Y",
) -> Tuple[np.ndarray, np.ndarray]:
    """Load a price CSV and return *trimmed* NumPy arrays.

    Parameters
    ----------
    path
        File path to the CSV that contains at least ``date_col`` and
        ``value_col``.
    start, end
        Desired visible window **inclusive**.  Accept anything that
        ``pandas.to_datetime`` understands, e.g. ``"2024‑01‑01"``.
    warmup
        Number of extra *calendar days* to include **before** ``start``.
        E.g. if your longest lag is 48 bars and you centre by four, use 52.
    date_col, value_col
        Column names in the CSV.  Defaults match the original script.
    date_format
        If the dates are fixed‑width (e.g. ``%m/%d/%Y``) you get a big speed
        boost by supplying the format; otherwise ``None`` lets pandas infer.

    Returns
    -------
    dates, prices
        Two one‑dimensional ``numpy.ndarray`` objects: ``datetime64[ns]`` and
        ``float`` respectively.  They are *already sorted* so you can use them
        directly for plotting or further processing.
    """

    # --- 1. read ----------------------------------------------------------------
    df = pd.read_csv(path, parse_dates=[date_col] if date_format is None else None)

    if date_format is not None:
        df[date_col] = pd.to_datetime(df[date_col], format=date_format, errors="coerce")

    # Drop rows with bad dates or NaNs in value column
    df = df.dropna(subset=[date_col, value_col])

    # Order is important for later slicing / vectorised ops
    df = df.sort_values(date_col).reset_index(drop=True)

    # --- 2. trim ----------------------------------------------------------------
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)

    if warmup:
        start_with_buffer = start_dt - pd.Timedelta(days=warmup)
    else:
        start_with_buffer = start_dt

    mask = (df[date_col] >= start_with_buffer) & (df[date_col] <= end_dt)
    df = df.loc[mask]

    # --- 3. return clean NumPy arrays ------------------------------------------
    dates = df[date_col].to_numpy(dtype="datetime64[ns]")
    prices = df[value_col].astype(float).to_numpy()

    if dates.size == 0:
        raise ValueError("No data left after trimming – check your date range or CSV contents.")

    return dates, prices


__all__ = [
    "load_prices",
]
