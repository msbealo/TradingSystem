"""plotting.py – unified helpers (UPDATED)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Matplotlib wrappers compatible with the driver script.

Changes in this revision
------------------------
* `plot_periodogram` now accepts `power_spectrum` **alias** (driver passes this)
  – internal code uses `power` var regardless of which keyword is supplied.
* Minor axis‑label tweaks.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional

__all__ = [
    "format_date_axis",
    "plot_convolution_dashboard",
    "plot_periodogram",
    "plot_acf_heatmap",
]

# --------------------------------------------------------------------
# Helper – month axis formatting
# --------------------------------------------------------------------

def format_date_axis(ax, month_interval: int = 2) -> None:
    """Apply %b %Y formatting to *ax* x‑axis."""
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=month_interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))


# --------------------------------------------------------------------
# Convolution dashboard
# --------------------------------------------------------------------

def plot_convolution_dashboard(
    *,
    dates: np.ndarray,
    prices: np.ndarray | None = None,
    price: np.ndarray | None = None,
    roof: np.ndarray,
    heat: np.ndarray,
    lookbacks: np.ndarray,
    signed_line: np.ndarray,
    r_sharp_baseline: np.ndarray,
    dominant_period: np.ndarray | None = None,
    title_prefix: str = "",
) -> plt.Figure:
    """Four‑panel convolution indicator dashboard.

    If *dominant_period* is supplied it will be over‑plotted as a cyan line on
    the heat‑map panel so you can visually confirm alignment with the hottest
    band.
    """
    # Accept both `price` and `prices` keyword
    if prices is None and price is not None:
        prices = price

    fig, axes = plt.subplots(
        4, 1, figsize=(15, 10), sharex=True,
        gridspec_kw={"height_ratios": [1, 1, 1, 0.6]},
    )

    # 1 Price panel
    axes[0].plot(dates, prices, color="black")
    axes[0].set_ylabel("Price")
    axes[0].set_title(f"{title_prefix} Price")
    axes[0].grid(True)

    # 2 Roofing filter panel
    axes[1].plot(dates, roof, color="blue")
    axes[1].set_ylabel("Roof")
    axes[1].set_title("Roofing Filter")
    axes[1].grid(True)

    # 3 Heat‑map panel
    extent = [mdates.date2num(dates[0]), mdates.date2num(dates[-1]), lookbacks[0], lookbacks[-1]]
    axes[2].imshow(heat, aspect="auto", origin="lower", extent=extent)
    axes[2].set_ylabel("Look‑back")
    axes[2].set_title("Convolution Heat‑map")

    # Overlay dominant period if provided
    if dominant_period is not None:
        axes[2].plot(dates, dominant_period, color="cyan", linewidth=1.0, label="Dom P")
        axes[2].legend(loc="upper left")

    # 4 Baseline convolution line
    axes[3].plot(dates, signed_line, color="purple", label="signed")
    axes[3].plot(dates, r_sharp_baseline, color="orange", linewidth=0.8, label="strength")
    axes[3].axhline(0, color="grey", linewidth=0.7)
    axes[3].set_ylabel("Signed Corr")
    axes[3].set_xlabel("Date")
    axes[3].set_title("Baseline Convolution")
    axes[3].grid(True)
    axes[3].legend(loc="upper left")

    for ax in axes:
        format_date_axis(ax)

    plt.tight_layout()
    return fig


# --------------------------------------------------------------------
# Periodogram
# --------------------------------------------------------------------

def plot_periodogram(
    *,
    dates: np.ndarray,
    roof: np.ndarray,
    power_spectrum: Optional[np.ndarray] = None,
    power: Optional[np.ndarray] = None,
    periods: np.ndarray,
    dominant_period: np.ndarray,
    title_prefix: str = "",
) -> plt.Figure:
    """Two‑panel Autocorrelation Periodogram plot.

    Accepts `power_spectrum` **or** `power` as alias – whichever is not None.
    """
    if power is None:
        if power_spectrum is None:
            raise ValueError("Must supply power_spectrum or power array")
        power = power_spectrum

    fig, axes = plt.subplots(2, 1, figsize=(15, 6), sharex=True,
                            gridspec_kw={"height_ratios": [1, 1]})

    # 1 Roofing filter for context
    axes[0].plot(dates, roof, color="blue")
    axes[0].set_ylabel("Roof")
    axes[0].set_title(f"{title_prefix} Roofing Filter")
    axes[0].grid(True)

    # 2 Periodogram heat‑map + DP line
    extent = [mdates.date2num(dates[0]), mdates.date2num(dates[-1]), periods[0], periods[-1]]
    axes[1].imshow(power, aspect="auto", origin="lower", extent=extent, cmap="inferno")
    axes[1].plot(dates, dominant_period, color="cyan", linewidth=1.0, label="Dominant P")
    axes[1].set_ylabel("Period (bars)")
    axes[1].set_title("Autocorrelation Periodogram")
    axes[1].legend(loc="upper left")

    for ax in axes:
        format_date_axis(ax)

    plt.tight_layout()
    return fig

# --------------------------------------------------------------------
# ACF heat‑map
# --------------------------------------------------------------------

def plot_acf_heatmap(
    *,
    dates: np.ndarray,
    prices: Optional[np.ndarray] = None,
    price: Optional[np.ndarray] = None,
    roof: Optional[np.ndarray] = None,
    lags: np.ndarray,
    acf: np.ndarray,
    title: str | None = None,
) -> plt.Figure:
    """Three‑panel ACF dashboard: *price*, *roof*, and heat‑map.

    Parameters
    ----------
    dates
        1‑D array of datetime64 or numeric x‑positions (length *N*).
    prices / price
        Raw price series to plot in panel 1.  Accept either keyword.
    roof
        Roofing‑filter series to plot in panel 2.  If `None`, this panel is
        skipped and only two panels are shown.
    lags
        1‑D integer array [1 .. max_lag] used for the y‑axis.
    acf
        2‑D float array (lags × time) – the autocorrelation matrix.
    title
        Optional overall figure title.
    """
    if prices is None and price is None:
        raise ValueError("pass prices= or price=")
    if prices is None:
        prices = price  # alias resolution

    # Decide layout – 3 panels if roof provided, else 2.
    has_roof = roof is not None
    nrows = 3 if has_roof else 2
    height_ratios = [1, 1, 1] if has_roof else [1, 1]

    fig, axes = plt.subplots(
        nrows, 1, figsize=(15, 8 if has_roof else 6), sharex=True,
        gridspec_kw={"height_ratios": height_ratios},
    )

    # Panel 0 – Price
    axes[0].plot(dates, prices, color="black")
    axes[0].set_ylabel("Price")
    axes[0].set_title(title or "Price / ACF Dashboard")
    axes[0].grid(True)

    # Panel 1 – Roofing filter (optional)
    if has_roof:
        axes[1].plot(dates, roof, color="blue")
        axes[1].set_ylabel("Roof")
        axes[1].set_title("Roofing Filter")
        axes[1].grid(True)
        hm_ax = axes[2]
    else:
        hm_ax = axes[1]

    # Panel last – Heat‑map
    extent = [mdates.date2num(dates[0]), mdates.date2num(dates[-1]), lags[0], lags[-1]]
    hm = hm_ax.imshow(acf, aspect="auto", origin="lower", extent=extent, cmap="PiYG", vmin=-1, vmax=1)
    hm_ax.set_ylabel("Lag (bars)")
    hm_ax.set_title("Autocorrelation Matrix")

    # Shared formatting
    for ax in axes:
        format_date_axis(ax)

    # Colour‑bar
    cbar = fig.colorbar(hm, ax=axes, orientation="vertical", fraction=0.015, pad=0.02)
    cbar.set_label("Correlation")

    plt.tight_layout()
    return fig
