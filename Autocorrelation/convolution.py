"""convolution.py
~~~~~~~~~~~~~~~~
Even-period convolution (folded Pearson-correlation) indicator à la John Ehlers.
This revision aligns the public API with the Phase-0 *driver.py* script so that
`convolution_heatmap()` now accepts explicit keyword arguments:

    convolution_heatmap(
        roof: np.ndarray,
        lookbacks: np.ndarray | None = None,
        shift: int = 4,
        baseline_L: int = 20,
    ) -> dict[str, np.ndarray]

* `lookbacks` —— 1-D array of **even** look-back lengths.  If *None*, the
  default is `np.arange(2, 49, 2)`.
* `shift` —— left-shift of the heat-map so that the indicator is centred
  (Ehlers uses 4 bars).
* `baseline_L` —— the single look-back length whose signed/sharpened series
  you want returned for a separate panel (defaults to 20).

Return value keys:

| key           | shape                      | description                               |
|---------------|----------------------------|-------------------------------------------|
| `heat`        | (len(lookbacks), T, 3)     | RGB cube 0-1                              |
| `signed_line` | (T,)                       | Fisher-sharpened *r* with ± sign          |
| `r`           | (T,)                       | raw Pearson *r* at `baseline_L`           |
| `r_sharp`     | (T,)                       | Fisher -sharpened |r| (0 -1) at baseline    |

All arrays include warm -up rows/cols so that the caller can slice them after
any desired buffer.

This module is **NumPy -only** and deliberately straightforward to read; you can
JIT -compile it with Numba later if speed becomes an issue.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Dict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

L_MIN, L_MAX = 2, 48                       # allowable range (even only)
LOOKBACKS = np.arange(L_MIN, L_MAX + 1)     # 2…48
LOOKBACKS = LOOKBACKS[LOOKBACKS % 2 == 0]   # skip odds
BASELINE_L = 20                             # default line row
SHIFT = 4                                   # visual left‑shift

# ---------------------------------------------------------------------------
# Helpers – Pearson r and Fisher transform
# -----------------------------------------------------------------------------

def _pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    """Folded Pearson correlation (arrays already demeaned)."""
    num = np.sum(x * y)
    den = np.sqrt(np.sum(x**2) * np.sum(y**2))
    return num / den if den else 0.0


def _inv_fisher(r: np.ndarray, k: float = 2.0) -> np.ndarray:
    """Return the Fisher-inverse transform bounded to (-1, 1)."""
    r = np.clip(r, -0.999, 0.999)
    return (np.exp(2 * k * r) - 1) / (np.exp(2 * k * r) + 1)


# -----------------------------------------------------------------------------
# Public: convolution_heatmap
# -----------------------------------------------------------------------------

def convolution_heatmap(
    roof: np.ndarray,
    lookbacks: np.ndarray | None = None,
    *,
    shift: int = SHIFT,
    baseline_L: int = BASELINE_L,
) -> Dict[str, np.ndarray]:
    """Compute the folded-Pearson convolution heat-map and baseline series.

    Parameters
    ----------
    roof
        The *roofing-filtered* price series (1-D NumPy array).
    lookbacks
        Iterable of even look-back lengths to include in the heat-map.  If
        *None*, defaults to `np.arange(2, 49, 2)`.
    shift
        Left-shift (number of bars) applied to each heat-map column so that the
        indicator is visually centred under the price bar where the Pearson
        correlation was computed.
    baseline_L
        One of the values in *lookbacks* whose signed/sharpened series is
        returned separately for plotting.
    """

    if lookbacks is None:
        lookbacks = np.arange(2, 49, 2)
    lookbacks = np.asarray(lookbacks, dtype=int)
    if np.any(lookbacks % 2):
        raise ValueError("All look-back lengths must be even (folded Pearson)")

    n = roof.size
    L_max = lookbacks.max()
    n_cols = n - L_max  # before slicing out warm-up or shift

    # Pre-allocate outputs
    heat = np.zeros((lookbacks.size, n_cols, 3), dtype=float)
    signed_line = np.full(n_cols, np.nan, dtype=float)
    r_line = np.full(n_cols, np.nan, dtype=float)
    r_sharp_line = np.full(n_cols, np.nan, dtype=float)

    # Map baseline_L to row index once
    try:
        baseline_idx = int(np.where(lookbacks == baseline_L)[0][0])
    except IndexError as exc:
        raise ValueError("baseline_L must be present in lookbacks") from exc

    # Main loop (pure-Python, but vectorisable with Numba if needed)
    for t in range(L_max, n):
        col = t - L_max - shift
        if not (0 <= col < n_cols):
            continue  # skip warm-up or right-edge where shift would underrun

        for row_idx, L in enumerate(lookbacks):
            if t < L:
                break  # insufficient history, all remaining Ls will also fail
            half = L // 2

            # Folded Pearson (even-period convolution)
            x = roof[t - np.arange(half)]
            y = roof[t - np.arange(L - 1, half - 1, -1)]

            xm, ym = x.mean(), y.mean()
            num = np.sum((x - xm) * (y - ym))
            den = np.sqrt(np.sum((x - xm) ** 2) * np.sum((y - ym) ** 2))
            r = num / den if den else 0.0

            r_sharp = _inv_fisher(r)
            sign = 1.0 if roof[t] - roof[t - L + 1] > 0 else -1.0

            # Heat-map pixel (RGB) – red for sign-negative, green for sign-positive
            sat = (r_sharp + 1.0) / 2.0  # 0-1 saturation
            heat[row_idx, col, 0 if sign == 1 else 1] = sat

            if row_idx == baseline_idx:
                signed_line[col] = r_sharp * sign
                r_line[col] = r
                r_sharp_line[col] = r_sharp

    return {
        "heat": heat,
        "signed_line": signed_line,
        "r": r_line,
        "r_sharp": r_sharp_line,
    }

def _evenise(val: float) -> int:
    """Round *val* to the nearest even integer within [2, 48]."""
    L = int(round(val))
    if L % 2:
        L += 1 if val > L else -1
    return max(L_MIN, min(L_MAX, L))

def map_dp_to_even(dp: np.ndarray, lookbacks: np.ndarray) -> np.ndarray:
    """Map dominant‑period float series → row index in *lookbacks* array.

    Returns an int array (rows) with -1 for out‑of‑range values.
    """
    even_L = 2 * np.round(dp / 2)
    even_L = even_L.astype(float)           # keep NaN for missing dp

    lb_to_idx = {L: i for i, L in enumerate(lookbacks)}
    row_idx = np.full(dp.size, -1, dtype=int)
    for t, L in enumerate(even_L):
        if np.isnan(L):
            continue
        row_idx[t] = lb_to_idx.get(int(L), -1)
    return row_idx

def baseline_from_dom(
    *,
    heat: np.ndarray,              # (rows × cols × 3)
    r_matrix: np.ndarray | None,   # optional (rows × cols)
    rsharp_matrix: np.ndarray | None,
    row_idx: np.ndarray,           # len ≥ cols + shift
    shift: int = 4,
):
    """Extract dynamic baseline series following Dominant Period.

    Returns:
        signed_line, raw_line, sharp_line  – 1‑D arrays length = cols
    """
    rows, cols, _ = heat.shape
    signed_line = np.full(cols, np.nan)
    raw_line    = np.full(cols, np.nan)
    sharp_line  = np.full(cols, np.nan)

    for col in range(cols):
        idx = row_idx[col + shift] if col + shift < row_idx.size else -1
        if idx < 0 or idx >= rows:
            continue
        # signed from heat (red‑green channel trick)
        red   = heat[idx, col, 0]
        green = heat[idx, col, 1]
        signed_line[col] = green - red     # +ve trough, ‑ve peak

        if r_matrix is not None and r_matrix.ndim == 2 and idx < r_matrix.shape[0]:
            raw_line[col] = r_matrix[idx, col]
        if (
            rsharp_matrix is not None
            and rsharp_matrix.ndim == 2
            and idx < rsharp_matrix.shape[0]
        ):
            sharp_line[col] = rsharp_matrix[idx, col]

    return signed_line, raw_line, sharp_line


def adaptive_convolution(
        roof: np.ndarray,
        dom_period: np.ndarray,
        *,
        lookbacks: np.ndarray | None = None,
        shift: int = 4,
        invert_fisher_k: float = 2.0,
) -> dict[str, np.ndarray]:
    """Adaptive convolution where look‑back L follows the dominant period.

    The heat‑map contains colour only in the row that corresponds to the chosen
    L for each column; other rows stay zero.  This mirrors the visual style of
    the fixed‑L version while reflecting the adaptive period.
    """
    n = len(roof)
    num_cols = n - L_MAX
    num_L = len(lookbacks)

    heat = np.zeros((num_L, num_cols, 3))
    signed_line = np.full(num_cols, np.nan)
    r_raw = np.full(num_cols, np.nan)
    r_sharp = np.full(num_cols, np.nan)
    L_chosen = np.full(num_cols, np.nan)

    for t in range(L_MAX, n):
        col = t - L_MAX - shift
        if not (0 <= col < num_cols):
            continue

        dp = dom_period[t]
        if np.isnan(dp):
            continue
        L = _evenise(dp)
        L_chosen[col] = L
        r_idx = np.where(lookbacks == L)[0][0]

        half = L // 2
        x = roof[t - np.arange(half)]
        y = roof[t - np.arange(L - 1, half - 1, -1)]
        r = _pearson_r(x - x.mean(), y - y.mean())
        r_shp = _inv_fisher(r, invert_fisher_k)
        sign = 1 if roof[t] - roof[t - L + 1] > 0 else -1
        sat = (r_shp + 1) / 2
        heat[r_idx, col, 0 if sign == 1 else 1] = sat

        signed_line[col] = r_shp * sign
        r_raw[col] = r
        r_sharp[col] = r_shp

    return {
        "heat": heat,
        "signed_line": signed_line,
        "r": r_raw,
        "r_sharp": r_sharp,
        "L_chosen": L_chosen,
    }