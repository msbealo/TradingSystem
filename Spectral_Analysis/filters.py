"""filters.py
~~~~~~~~~~~~~~~~
Reusable Ehlers-style signal-processing filters.

All routines accept **NumPy** arrays and return **NumPy** arrays so they can be
composed easily.  The implementation follows John Ehlers' DSP formulations
(2-pole high-pass and 2-pole Super Smoother low-pass).

The key export is `roofing_filter`, which you can plug straight into the
existing convolution-indicator and Autocorrelation Periodogram code.

Example
-------
>>> from filters import roofing_filter
>>> hp, roof = roofing_filter(prices, hp_period=80, lp_period=40)
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np

__all__ = [
    "high_pass_filter",
    "super_smoother_filter",
    "roofing_filter",
]

def _two_pole_high_pass_coeffs(period: float) -> tuple[float, float]:
    """Internal helper to compute *alpha1* and (1-alpha1/2)^2 for the 2-pole HP.
    Parameters
    ----------
    period : float
        The *-3 dB* (cut-off) period in bars.
    Returns
    -------
    alpha1 : float
    k      : float
        Where *k* = (1 - alpha1/2)^2.  Pre-computing saves work in the loop.
    """
    rad = math.sqrt(2) * math.pi / period
    alpha1 = (math.cos(rad) + math.sin(rad) - 1.0) / math.cos(rad)
    k = (1.0 - alpha1 / 2.0) ** 2
    return alpha1, k

def high_pass_filter(x: np.ndarray, period: int | float = 80) -> np.ndarray:
    """2-pole high-pass filter (Ehlers).

    Removes cycles ***longer*** than *period* bars.
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    alpha1, k = _two_pole_high_pass_coeffs(period)
    hp = np.zeros_like(x, dtype=float)

    # Start at index 2 because the recurrence uses t-1 and t-2 samples.
    for i in range(2, len(x)):
        hp[i] = (
            k * (x[i] - 2.0 * x[i - 1] + x[i - 2])
            + 2.0 * (1.0 - alpha1) * hp[i - 1]
            - (1.0 - alpha1) ** 2 * hp[i - 2]
        )
    return hp

def _super_smoother_coeffs(period: float) -> tuple[float, float, float]:
    """Return (c1, c2, c3) for the Super Smoother of given *period*."""
    a1 = math.exp(-math.sqrt(2) * math.pi / period)
    b1 = 2.0 * a1 * math.cos(math.sqrt(2) * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    return c1, c2, c3

def super_smoother_filter(
    x: np.ndarray, period: int | float = 10, *, initial: float | None = None
) -> np.ndarray:
    """2-pole Super Smoother low-pass filter.

    Parameters
    ----------
    x : ndarray
        Input signal.
    period : int | float, default=10
        -3 dB period.  Ehlers often uses *10*.
    initial : float | None, default=None
        Optional initial value to seed the filter; if *None* the first
        two outputs are set equal to *x[0]*.
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    c1, c2, c3 = _super_smoother_coeffs(period)
    out = np.zeros_like(x, dtype=float)

    # Seed first two values
    out[0] = x[0] if initial is None else initial
    out[1] = out[0]

    for i in range(2, len(x)):
        out[i] = (
            c1 * (x[i] + x[i - 1]) / 2.0
            + c2 * out[i - 1]
            + c3 * out[i - 2]
        )
    return out

def roofing_filter(
    prices: np.ndarray,
    *,
    hp_period: int | float = 80,
    lp_period: int | float = 40,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (*hp*, *roof*) arrays after applying HP then Super Smoother.

    This is the classic *Roofing Filter* described by John Ehlers:

    1. 2-pole high-pass (cut-off `hp_period`)
    2. 2-pole Super Smoother low-pass (cut-off `lp_period`)

    Notes
    -----
    The defaults (80, 40) mimic the parameters used in your existing script.
    """
    hp = high_pass_filter(prices, period=hp_period)
    roof = super_smoother_filter(hp, period=lp_period)
    return hp, roof
