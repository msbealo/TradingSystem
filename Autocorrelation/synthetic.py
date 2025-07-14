"""synthetic.py
~~~~~~~~~~~~~~~~~~~~~~~~
Synthetic market‑like price series generator for stress‑testing the Ehlers
Toolkit.  Produces a signal that is a sum of sinusoids whose amplitudes follow
a 1/f^α spectrum ("pink" noise) plus optional white noise for a chosen
signal‑to‑noise ratio (SNR).

Public API
----------
make_signal(
    n_bars: int,
    periods: list[int] | None = None,
    *,
    alpha: float = 1.0,
    random_phases: bool = True,
    snr_db: float | None = None,
    dt: float = 1.0,
    seed: int | None = None,
) -> np.ndarray
    Generate a NumPy array of length *n_bars*.

Example
-------
>>> import synthetic as syn
>>> y = syn.make_signal(1024, periods=[20, 40], snr_db=10, seed=0)
>>> y.shape
(1024,)
"""
from __future__ import annotations

import math
import numpy as np
from numpy.typing import NDArray

__all__ = ["make_signal"]


def _ensure_rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(None if seed is None else seed)


def make_signal(
    n_bars: int,
    periods: list[int] | None = None,
    *,
    alpha: float = 2,
    random_phases: bool = True,
    snr_db: float | None = None,
    dt: float = 1.0,
    seed: int | None = None,
) -> NDArray[np.float64]:
    """Return a synthetic price‑like series.

    Parameters
    ----------
    n_bars
        Number of samples (bars) to generate.
    periods
        List of integer cycle lengths (in bars).  If *None*, we create a set of
        harmonics whose fundamental is *n_bars/4* down to 10 bars, roughly 8–10
        components.
    alpha
        Spectral slope for amplitude scaling, *A_p ∝ 1/p^alpha*.
    random_phases
        If *True*, each component gets a random phase ∈ [0, 2π).  Otherwise
        phases are 0 so the sinusoids align.
    snr_db
        Desired signal‑to‑noise ratio in **dB**.  If *None* or ``math.inf`` no
        noise is added.
    dt
        Sample spacing (ignored by signal itself, useful when generating a time
        vector externally).
    seed
        RNG seed for reproducibility.

    Notes
    -----
    *The generated series is centred (zero‑mean) and roughly unit‑variance
    before noise is added, so *snr_db* refers to power ratio relative to that
    baseline.*
    """
    rng = _ensure_rng(seed)

    if periods is None:
        max_p = max(10, n_bars // 4)
        periods = list(range(max_p, 9, -5))  # e.g. [256, 251, 246, ... 10]

    periods = np.asarray(periods, dtype=float)
    amps = 1.0 / periods**alpha
    amps /= np.max(amps)  # normalise largest amplitude to 1

    # Optional random phases
    if random_phases:
        phases = rng.uniform(0, 2 * math.pi, size=len(periods))
    else:
        phases = np.zeros(len(periods))

    t = np.arange(n_bars) * dt
    signal = np.sum(
        amps[:, None] * np.sin(2 * math.pi * (1 / periods)[:, None] * t + phases[:, None]),
        axis=0,
    )

    # Centre & scale to unit variance (roughly)
    signal -= signal.mean()
    signal_sd = signal.std(ddof=0)
    if signal_sd > 0:
        signal /= signal_sd

    # Add white noise for desired SNR
    if snr_db is not None and math.isfinite(snr_db):
        snr_linear = 10 ** (snr_db / 10)
        noise_var = 1 / snr_linear
        noise = rng.normal(scale=math.sqrt(noise_var), size=n_bars)
        signal += noise

    return signal.astype(float)
