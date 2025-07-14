import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ------------------ Load and window gold data ------------------
df = (
    pd.read_csv("Gold-10years.csv", skiprows=12, names=["date", "price"])
    .query("date.str.match(r'\\d{4}-\\d{2}-\\d{2}')", engine="python")
    .assign(date=lambda d: pd.to_datetime(d["date"]),
            price=lambda d: pd.to_numeric(d["price"], errors="coerce"))
    .dropna()
    .sort_values("date")
    .query("date >= '2014-01-01' and date <= '2017-12-31'")
    .reset_index(drop=True)
)

dates = df["date"].values
price = df["price"].values

# ------------------ Ehlers two‑pole HP & SuperSmoother helpers ------------------
def alpha_ehlers(K: float, period: float) -> float:
    c = np.cos(2 * np.pi * K / period)
    s = np.sin(2 * np.pi * K / period)
    return (c + s - 1) / c

def two_pole_highpass(series: np.ndarray, period: float) -> np.ndarray:
    α = alpha_ehlers(0.707, period)          # K = 0.707 → 2‑pole HP
    b0, b1, b2 = (1 - α) / 2, -(1 - α), (1 - α) / 2
    a1, a2 = -2 * (1 - α), (1 - α) ** 2
    hp = np.zeros_like(series)
    for i in range(2, len(series)):
        hp[i] = (b0 * series[i] + b1 * series[i - 1] + b2 * series[i - 2]
                 - a1 * hp[i - 1] - a2 * hp[i - 2])
    return hp

def supersmoother(series: np.ndarray, period: float) -> np.ndarray:
    α = alpha_ehlers(1.414, period)          # K = 1.414 → 2‑pole LP
    b0 = α ** 2
    a1, a2 = -2 * (1 - α), (1 - α) ** 2
    lp = np.zeros_like(series)
    for i in range(2, len(series)):
        lp[i] = (b0 * series[i] + 2 * b0 * series[i - 1] + b0 * series[i - 2]
                 - a1 * lp[i - 1] - a2 * lp[i - 2])
    return lp

# ------------------ Roofing filter (HP 64, SS 8) ------------------
hp64 = two_pole_highpass(price, 64)
roofed = supersmoother(hp64, 8)

# ------------------ Autocorrelation matrix ------------------
max_lag = 48
n = len(roofed)
ac_matrix = np.full((max_lag, n), np.nan)

for lag in range(1, max_lag + 1):
    L = lag  # averaging window equals lag
    x = np.roll(roofed, lag)
    x[:lag] = np.nan  # ensure causality
    y = roofed
    sx = pd.Series(x).rolling(L).sum()
    sy = pd.Series(y).rolling(L).sum()
    sxx = pd.Series(x**2).rolling(L).sum()
    syy = pd.Series(y**2).rolling(L).sum()
    sxy = pd.Series(x*y).rolling(L).sum()
    num = L * sxy - sx * sy
    den = np.sqrt((L * sxx - sx**2) * (L * syy - sy**2))
    r = num / den
    ac_matrix[lag-1] = ((r + 1) / 2).values  # scale to [0,1]

# ------------------ Plot ------------------
fig, axs = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

# Gold price
axs[0].plot(dates, price, color='tab:orange')
axs[0].set_title("Gold Price (2014–2017)")
axs[0].grid(True)

# Autocorrelation heat map
extent = [0, n, 1, max_lag]
im = axs[1].imshow(ac_matrix, aspect='auto', origin='lower',
                   cmap='RdYlGn', extent=extent, interpolation='nearest')
axs[1].set_ylabel("Lag (bars)")
axs[1].set_title("Ehlers Autocorrelation Indicator\nRoofing = HP‑64 + SuperSmoother‑8  (window length = lag)")
# Convert x-axis ticks to dates
ticks = np.linspace(0, n-1, 8, dtype=int)
axs[1].set_xticks(ticks)
axs[1].set_xticklabels(pd.to_datetime(dates[ticks]).strftime('%Y-%m-%d'),
                       rotation=45, ha='right')
axs[1].set_xlabel("Date")

cbar = fig.colorbar(im, ax=axs[1])
cbar.set_label("Scaled Correlation (0 = red, 1 = green)")

plt.tight_layout()
