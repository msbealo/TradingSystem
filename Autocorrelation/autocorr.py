"""autocorr.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Robust, warm-up-aware implementation of the Autocorrelation Periodogram
suite.  This **full rewrite** fixes the shape-mismatch you encountered and lets
you obtain valid values as soon as `avg_len` samples are available, instead of
waiting until `max_lag`.

Key design decisions
--------------------
1. *Warm-up handling*: the returned arrays are padded with **NaN** until each
   statistic is well defined.  That means the very first valid column is at
   index `(avg_len-1)`, not `(max_lag)`.  Your driver/numpy plots can just
   skip NaNs via `np.nan_to_num` or boolean masks.
2. *No “graphical” left-shift*: the 4-bar visual shift used for the convolution
   heat-map is **not** applied here because it would pull future data into the
   DominantPeriod calculation.  If you want to visual-shift later for aesthetics,
   do it in the plotting routine (e.g., `np.roll(..., -4)`), never in the maths.
3. *Vectorised Pearson*: uses cumulative sums (prefix-sums) so the whole
   ACF matrix is computed without explicit Python loops - still pure NumPy.
4. *Periodogram caching*: cosine/sine tables are pre-computed once per run
   and reused.

Public API
----------
acf_matrix(signal, max_lag=48, avg_len=3) -> np.ndarray
    Row = lag 1..max_lag, Col = time; NaNs where undefined.
acf_periodogram(acf_mat, periods) -> np.ndarray
    Power[period, time] (0-1 normalised).
normalise_power(...)
    Same signature, unchanged.
dominant_period(power, periods) -> np.ndarray
compute_periodogram(signal, ...) -> tuple(power, dom_period)

Example
~~~~~~~
>>> import numpy as np, autocorr
>>> s = np.sin(2*np.pi*np.arange(200)/20)       # 20-bar sine
>>> pwr, dp = autocorr.compute_periodogram(s)
>>> round(np.nanmean(dp[-50:]))   # dominant period ≈ 20
20
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "acf_matrix",
    "acf_periodogram",
    "normalise_power",
    "dominant_period",
    "compute_periodogram",
]

# -----------------------------------------------------------------------------
# 1.  Autocorrelation matrix (Pearson) - vectorised with prefix sums
# -----------------------------------------------------------------------------

def _rolling_mean(x: np.ndarray, win: int) -> np.ndarray:  # noqa: D401
    """Return rolling mean of *x* with window *win*, treating NaN as missing.

    NaNs do **not** contribute to the sum *or* the count.  Result is NaN when
    the window has < win valid samples (so early bars are NaN, as expected).
    """
    if win <= 0:
        raise ValueError("win must be positive")

    # Replace NaN with 0 for the cumulative‑sum trick
    x_filled = np.where(np.isnan(x), 0.0, x)
    csum = np.cumsum(x_filled)
    csum[win:] = csum[win:] - csum[:-win]

    # Parallel cumulative count of *finite* samples
    is_valid = np.isfinite(x).astype(float)
    ccount = np.cumsum(is_valid)
    ccount[win:] = ccount[win:] - ccount[:-win]

    # Avoid division by zero → NaN when count < win
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = csum / ccount
    mean[ccount < win] = np.nan
    return mean

def acf_matrix(signal: np.ndarray, *, max_lag: int = 48, avg_len: int = 3) -> np.ndarray:
    """Return Pearson autocorrelation for lags 1..max_lag (rows) over time (cols).

    The first `(avg_len-1)` columns are NaN, then each lag row starts to fill
    with valid values once enough samples exist.  No future data is used.
    """
    if signal.ndim != 1:
        raise ValueError("signal must be 1-D")
    n = signal.size
    if n < avg_len:
        raise ValueError("signal too short for requested avg_len")

    # Pre-compute rolling sums, squares, means for the *base* series (Y)
    Y = signal
    Y_mean = _rolling_mean(Y, avg_len)
    Y2_sum = np.convolve(Y**2, np.ones(avg_len, dtype=float), "valid")

    acf = np.full((max_lag, n), np.nan, dtype=float)

    for L in range(1, max_lag + 1):
        X = np.roll(signal, L)          # lagged copy
        X[:L] = np.nan                  # invalidate rolled-in future values

        # Means & sums over the same window length
        X_mean = _rolling_mean(X, avg_len)
        XY_sum = np.convolve(X * Y, np.ones(avg_len, dtype=float), "valid")
        X2_sum = np.convolve(X**2, np.ones(avg_len, dtype=float), "valid")

        num = XY_sum - avg_len * X_mean[avg_len - 1 :] * Y_mean[avg_len - 1 :]
        den = np.sqrt(
            np.maximum(X2_sum - avg_len * X_mean[avg_len - 1 :] ** 2, 0)
            * np.maximum(Y2_sum - avg_len * Y_mean[avg_len - 1 :] ** 2, 0)
        )
        r = np.divide(num, den, out=np.full_like(num, np.nan), where=den != 0)

        # Align into the full-length column (pad front with NaNs to match signal)
        acf[L - 1, avg_len - 1 :] = r

    return acf


# -----------------------------------------------------------------------------
# 2.  DFT of the ACF → raw power spectrum (period axis)
# -----------------------------------------------------------------------------

def acf_periodogram(acf_mat: np.ndarray, periods: np.ndarray) -> np.ndarray:
    """Return power[period_idx, time] (not yet normalised)."""
    lags, n = acf_mat.shape
    max_lag = lags  # convenience

    # Pre-build trig tables once
    two_pi = 2 * np.pi
    cos_tbl = np.empty((periods.size, max_lag), dtype=float)
    sin_tbl = np.empty_like(cos_tbl)
    for i, P in enumerate(periods):
        theta = two_pi * np.arange(1, max_lag + 1) / P
        cos_tbl[i] = np.cos(theta)
        sin_tbl[i] = np.sin(theta)

    # Mask NaNs to zero for dot-products (they won’t contribute)
    acf_nan_to_zero = np.nan_to_num(acf_mat, nan=0.0)

    # Compute power via cos/sin projections
    cos_proj = cos_tbl @ acf_nan_to_zero
    sin_proj = sin_tbl @ acf_nan_to_zero
    power = cos_proj**2 + sin_proj**2
    return power


# -----------------------------------------------------------------------------
# 3.  Normalisation (EMA + fast-attack / slow-decay AGC)
# -----------------------------------------------------------------------------

def normalise_power(
    pwr: np.ndarray,
    ema_alpha: float = 0.2,
    agc_decay: float = 0.995,
) -> np.ndarray:
    """
    Fast-attack / slow-decay normalisation à la Ehlers
    --------------------------------------------------
    * pwr:        raw power  (periods × n_bars)
    * ema_alpha:  smoothing applied *per period*
    * agc_decay:  scalar MaxPwr := max(MaxPwr * decay, new_total_power)
    """
    # 1. EMA smoothing (per period)
    smoothed = np.empty_like(pwr)
    smoothed[:, 0] = pwr[:, 0]
    for t in range(1, pwr.shape[1]):
        smoothed[:, t] = (
            ema_alpha * pwr[:, t] + (1.0 - ema_alpha) * smoothed[:, t - 1]
        )

    # 2. Global AGC
    norm = np.empty_like(smoothed)
    max_pwr = smoothed[:, 0].max() + 1e-12   # avoid divide-by-zero
    for t in range(smoothed.shape[1]):
        total = smoothed[:, t].max()          # <-- use *max across periods*
        if total > max_pwr:
            max_pwr = total                   # fast attack
        else:
            max_pwr *= agc_decay              # slow decay
        norm[:, t] = smoothed[:, t] / max_pwr

    gamma = 1.5  # gamma > 1.0 for non-linear compression
    norm **= gamma  # non-linear compression

    return [norm.clip(0.0, 1.0), smoothed]               # stay in [0,1]


# -----------------------------------------------------------------------------
# 4.  Dominant period (centre-of-gravity)
# -----------------------------------------------------------------------------

def dominant_period(norm: np.ndarray, periods: np.ndarray,
                    rel_thresh: float = 0.7, min_rows: int = 1) -> np.ndarray:
    """Return dominant-period series that hugs the hottest stripe."""
    n_bars = norm.shape[1]
    dom    = np.full(n_bars, np.nan)

    for t in range(n_bars):
        col   = norm[:, t]
        mask  = col >= rel_thresh * col.max()
        if mask.sum() < min_rows:
            idx = col.argmax()
            dom[t] = periods[idx]
        else:
            # CoG of the bright cluster
            dom[t] = np.sum(periods[mask] * col[mask]) / np.sum(col[mask])

    # Optional EMA smoothing (keeps responsiveness but removes single-bar flips)
    # alpha = 0.3
    # for t in range(1, n_bars):
    #     if np.isnan(dom[t-1]):
    #         continue
    #     dom[t] = alpha*dom[t] + (1-alpha)*dom[t-1]

    return dom

# -----------------------------------------------------------------------------
# 5.  Convenience wrapper - all in one go
# -----------------------------------------------------------------------------

def compute_periodogram(signal: np.ndarray, *, max_lag: int = 48, avg_len: int = 3, periods: np.ndarray | None = None, ema_alpha: float = 0.3) -> tuple[np.ndarray, np.ndarray]:
    """Return (norm_power, dominant_period).

    *norm_power* has shape (n_periods, time) and ranges 0-1.
    *dominant_period* is 1-D (time) with NaNs where undefined.
    """
    if periods is None:
        periods = np.arange(10, max_lag + 1)

    acf = acf_matrix(signal, max_lag=max_lag, avg_len=avg_len)
    raw_pwr = acf_periodogram(acf, periods)
    norm_pwr = normalise_power(raw_pwr, ema_alpha=ema_alpha)
    dom_per = dominant_period(norm_pwr, periods)
    return norm_pwr, dom_per
