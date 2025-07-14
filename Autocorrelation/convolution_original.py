import math, numpy as np, pandas as pd
import matplotlib.pyplot as plt, matplotlib.dates as mdates

# 0. How much extra data do we need for warm-up?
hp_period, lp_period = 80, 40
L_min, L_max  = 1, 48
LOKBACK_LINE  = 20                  # the line we want to plot later
shift         = 4                   # 4-bar left-shift à la Ehlers

# ------------------------------------------------------------------
# 1.  Load data (last 12 months)
# ------------------------------------------------------------------
df = pd.read_csv('Gold-10years_250714.csv')
df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')
end_date   = df['Date'].max()
plot_start = end_date - pd.DateOffset(years=1)           # what we SHOW
buffer = L_max + shift          # 48 + 4 = 52 bars
load_start = plot_start - pd.DateOffset(days=buffer)     # what we LOAD
df = df[df['Date'] >= load_start].reset_index(drop=True)

dates   = df['Date'].values
prices  = df['Value'].astype(float).values
n       = len(prices)

# ------------------------------------------------------------------
# 2.  Roofing filter (HP 80, LP 20)
# ------------------------------------------------------------------

hp   = np.zeros(n)
roof = np.zeros(n)

rad_hp = math.sqrt(2)*math.pi/hp_period
alpha1 = (math.cos(rad_hp) + math.sin(rad_hp) - 1) / math.cos(rad_hp)

a1 = math.exp(-math.sqrt(2)*math.pi/lp_period)
b1 = 2*a1*math.cos(math.sqrt(2)*math.pi/lp_period)
c2, c3 = b1, -a1*a1
c1 = 1 - c2 - c3

for i in range(2, n):
    hp[i]   = (1-alpha1/2)**2*(prices[i]-2*prices[i-1]+prices[i-2]) \
              + 2*(1-alpha1)*hp[i-1] - (1-alpha1)**2*hp[i-2]
    roof[i] = c1*(hp[i]+hp[i-1])/2 + c2*roof[i-1] + c3*roof[i-2]
    # roof[i] = c1*(prices[i]+prices[i-1])/2 + c2*roof[i-1] + c3*roof[i-2]

# ------------------------------------------------------------------
# 3. Convolution heat-map (look-backs 3-48) –- *skip odd periods*
# ------------------------------------------------------------------


lookbacks = np.arange(L_min, L_max + 1)
lookbacks = lookbacks[lookbacks % 2 == 0]      # skip odds
idx_20    = np.where(lookbacks == LOKBACK_LINE)[0][0]   # row index of 20-bar band

num_L = len(lookbacks)
num_t = n - L_max                     # columns before trimming
heat   = np.zeros((num_L, num_t, 3))  # RGB image
line   = np.full(num_t, np.nan)       # 20-bar signed-sharp series
r_20   = np.full(num_t, np.nan)       # 20-bar signed-sharp series
r_sharp_20 = np.full(num_t, np.nan)  # 20-bar signed-sharp series

def inv_fisher(r):
    r = np.clip(r, -0.999, 0.999)
    k = 2
    return (np.exp(2*k*r) - 1) / (np.exp(2*k*r) + 1)

# ---------------------------------------------------------------
# UNIFIED LOOP:  iterate over every time index t ≥ L_max
# ---------------------------------------------------------------
for t in range(L_max, n):
    col = t - L_max - shift           # column after the 4-bar centring shift
    if not (0 <= col < num_t):
        continue                      # skip warm-up columns

    for r_idx, L in enumerate(lookbacks):
        if t < L:                     # not enough look-back yet
            continue
        half = L // 2

        # --- Pearson r on folded halves ---
        x = roof[t - np.arange(half)]
        y = roof[t - np.arange(L-1, half-1, -1)]
        num = np.sum((x - x.mean()) * (y - y.mean()))
        den = np.sqrt(np.sum((x - x.mean())**2) * np.sum((y - y.mean())**2))
        r   = num / den if den else 0.0

        r_sharp = inv_fisher(r)           # same sharpening for *both* outputs
        sign    = 1 if roof[t] - roof[t-L+1] > 0 else -1

        # --- Heat-map pixel ---
        sat = (r_sharp + 1) / 2           # 0-1 saturation just for colour
        heat[r_idx, col, 0 if sign == 1 else 1] = sat

        # --- 20-bar line (pick row once) ---
        if r_idx == idx_20:
            line[col] = r_sharp * sign    # store already shifted
            r_20[col] = r
            r_sharp_20[col] = r_sharp

# ------------------------------------------------------------------
# map a heat-map column j  ⇔  data index  t = j + L_max + shift
# ------------------------------------------------------------------
# convert the scalar Timestamp → numpy.datetime64
plot_start_np = np.datetime64(plot_start)

t0_window  = np.searchsorted(dates, np.datetime64(plot_start), side='left')
col_start  = max(0, t0_window - (L_max + shift))       # warm-up trim
t_first    = L_max + shift + col_start                 # ← unified start

# ------------------------------------------------------------------
# 5.  Plot: four vertically stacked panels
# ------------------------------------------------------------------
# x-axis for every panel
dates_disp   = dates[t_first :]

# panels 1 & 2
prices_disp  = prices[t_first :]
hp_disp     = hp[t_first :]
roof_disp    = roof[t_first :]

# panel 3: colour map
heat_disp    = heat[:, col_start + shift :]                    # columns align with t_first

# panel 4: 20-bar line
line_disp    = line[col_start + shift:]                       # same columns ⇒ same x
r_20_disp   = r_20[col_start + shift:]                      # same columns ⇒ same x
r_sharp_20_disp = r_sharp_20[col_start + shift:]  # same columns ⇒ same x

fig, axes = plt.subplots(
    4, 1, figsize=(15, 10), sharex=True,
    gridspec_kw={'height_ratios': [1, 1, 1, 0.6]})

# ★ 5-1 price  (trimmed arrays)
axes[0].plot(dates_disp, prices_disp, color='black')
axes[0].set_ylabel('USD/oz')
axes[0].set_title('Gold price (last 12 months)')
axes[0].grid(True)

# ★ 5-2 roofing filter  (trimmed)
axes[1].plot(dates_disp, roof_disp, color='blue')
axes[1].set_ylabel('Roofing value')
axes[1].set_title('Ehlers roofing filter')
axes[1].grid(True)

# 5-3 heat-map  (already trimmed to heat_plot)
extent = [
    mdates.date2num(dates_disp[0]),         # ★ start at plot window
    mdates.date2num(dates_disp[-1]),        #   end at plot window
    L_min, L_max]
axes[2].imshow(heat_disp, aspect='auto', origin='lower', extent=extent)
axes[2].set_ylabel('Look-back (bars)')
axes[2].set_title('Convolution heat-map (red = peak, green = trough)')

# ★ 5-4 20-bar convolution  (use trimmed conv20_plot & conv_dates)
axes[3].plot(dates_disp, line_disp, color='purple')
axes[3].plot(dates_disp, r_sharp_20_disp,  color='orange', linewidth=0.8,
             label='strength (unsigned)')
axes[3].axhline(0, color='grey', linewidth=0.7)
axes[3].set_ylabel('Signed corr')
axes[3].set_xlabel('Date')
axes[3].set_title('Signed, sharpened 20-bar convolution')
axes[3].grid(True)

# format x-axis
for ax in axes:
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))

plt.tight_layout()
plt.show()