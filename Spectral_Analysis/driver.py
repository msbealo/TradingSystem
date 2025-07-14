"""driver.py – Phase‑1 end‑to‑end demo (UPDATED)
================================================
Loads price data, builds the roofing filter, convolution heat‑map, and
Autocorrelation Periodogram, then plots both dashboards.

Run:
    python driver.py  # assumes Gold-10years.csv in cwd
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import price_io as io_mod
import filters
import convolution
import autocorr
import plotting
from synthetic import make_signal  # for testing, not used in production

# ---------------------------------------------------------------------------
# Parameters & I/O
# ---------------------------------------------------------------------------
CSV_PATH = Path("Gold-10years.csv")
PLOT_WINDOW_YEARS = 1
HP_PERIOD_CONV, LP_PERIOD_CONV = 80, 40
HP_PERIOD_AC, LP_PERIOD_AC = 48, 10
MAX_LAG = 48
LOOKBACKS = np.arange(2, MAX_LAG + 1, 2)  # even only
SHIFT = 4  # 4-bar left-shift (Ehlers style)

if not CSV_PATH.exists():
    sys.exit(f"CSV not found: {CSV_PATH}")

end_date = datetime(2025, 7, 1)
plot_start = end_date - timedelta(days=365 * PLOT_WINDOW_YEARS)
load_start = plot_start - timedelta(days=MAX_LAG + SHIFT)

# ── parameters ──────────────────────────────────────────────────────────
synthetic = False                         # turn ON synthetic testing
n_bars    = 365*2                          # how many bars you want (≈ 1 year)
                                         # or reuse len(raw_dates) if you like
periods   = [20]                     # synthetic cycle periods
snr_db    = None                           # signal-to-noise ratio (dB) or None
# -----------------------------------------------------------------------

if synthetic:
    # 1) Build a *smooth* business-day date range ending today
    end_date   = pd.Timestamp.today().normalize()
    raw_dates  = pd.date_range(end=end_date, periods=n_bars, freq="D").to_numpy()

    # 2) Generate the synthetic price series
    raw_prices = make_signal(
        n_bars=n_bars,
        periods=periods,
        snr_db=snr_db,
        random_phases=True,
        alpha=1.0,           # 1/f amplitude profile (market-like)
    )

else:
    # ← original CSV branch (kept intact)
    raw_dates, raw_prices = io_mod.load_prices(
        CSV_PATH,
        start=load_start,
        end=end_date,
        date_col="Date",
        value_col="Value",
    )
# ---------------------------------------------------------------------------
# Signal processing
# ---------------------------------------------------------------------------
_, roof_conv = filters.roofing_filter(raw_prices, hp_period=HP_PERIOD_CONV, lp_period=LP_PERIOD_CONV)
_, roof_ac = filters.roofing_filter(raw_prices, hp_period=HP_PERIOD_AC, lp_period=LP_PERIOD_AC)

conv_out = convolution.convolution_heatmap(
    roof=roof_conv,
    lookbacks=LOOKBACKS,
    shift=SHIFT,
    baseline_L=40,
)

acf = autocorr.acf_matrix(roof_ac, max_lag=MAX_LAG, avg_len=2)
periods = np.arange(10, MAX_LAG + 1)
raw_power = autocorr.acf_periodogram(acf, periods)
[norm_power, ema] = autocorr.normalise_power(raw_power, ema_alpha=0.3, agc_decay=0.991)
DomP = autocorr.dominant_period(norm_power, periods, rel_thresh=0.7)

# After computing heat, r, r_sharp with convolution_heatmap
row_idx = convolution.map_dp_to_even(DomP, LOOKBACKS)   # 1-D, no shift applied

signed_line_dp, r_line_dp, r_sharp_dp = convolution.baseline_from_dom(
    heat=conv_out['heat'],
    r_matrix=conv_out['r'],              # 1-D baseline OK
    rsharp_matrix=conv_out['r_sharp'],  # 1-D baseline OK
    row_idx=row_idx,
    shift=SHIFT,                  # same 4-bar visual shift
)


# ---------------------------------------------------------------------------
# Align slices (start at t = MAX_LAG + SHIFT)
# ---------------------------------------------------------------------------
start_idx = MAX_LAG + SHIFT

dates_vis = raw_dates[start_idx:]
price_vis = raw_prices[start_idx:]
roof_conv_vis = roof_conv[start_idx:]
roof_ac_vis = roof_ac[start_idx:]

heat_vis = conv_out["heat"][:, SHIFT:]
line_vis = conv_out["signed_line"][SHIFT:]
r_sharp_vis     = r_sharp_dp[SHIFT:]
signed_line_vis = signed_line_dp[SHIFT:]

power_vis = norm_power[:, start_idx:]
DomP_vis = DomP[start_idx:]

# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
lags = np.arange(1, MAX_LAG + 1)
acf_fig = plotting.plot_acf_heatmap(
    dates=dates_vis,
    prices=price_vis,
    roof=roof_ac_vis,
    lags=np.arange(1, MAX_LAG + 1),
    acf=acf[:, MAX_LAG+SHIFT:],   # trim warm-up
    title="Autocorrelation Heat-map",
)

plotting.plot_convolution_dashboard(
    dates=dates_vis,
    prices=price_vis,
    roof=roof_conv_vis,
    heat=heat_vis,
    lookbacks=LOOKBACKS,
    signed_line=signed_line_vis,
    r_sharp_baseline=r_sharp_vis,
    dominant_period=DomP_vis,          # still draws cyan track
)

plotting.plot_periodogram(
    dates=dates_vis,
    roof=roof_ac_vis,
    power_spectrum=power_vis,
    periods=periods,
    dominant_period=DomP_vis,
)

plt.show()

# ---------------------------------------------------------------------
# Test synthetic signal generation (optional)

# # Pure 20-bar sine, no noise
# max_lag=48
# low_period = 10  # low-pass period for roofing filter
# sig    = np.sin(2*np.pi*np.arange(600)/20)

# hp, roof = filters.roofing_filter(sig, hp_period=48, lp_period=10)
# acf      = autocorr.acf_matrix(roof, max_lag=max_lag, avg_len=20)

# # skip lags 1 & 2 for cleaner projection
# periods = np.arange(low_period, max_lag + 1)
# power = autocorr.acf_periodogram(acf[2:], np.arange(low_period, 49))

# [norm_power, ema] = autocorr.normalise_power(power, ema_alpha=0.3, agc_decay=0.991)

# plt.imshow(norm_power, origin='lower', aspect='auto',
#            extent=[0, sig.size, periods[0], periods[-1]])
# plt.axhline(20, color='cyan'); plt.title('20-bar synthetic'); plt.show()
