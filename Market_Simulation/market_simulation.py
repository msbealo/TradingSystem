import numpy as np
import random
import matplotlib.pyplot as plt
import time

# Start the timer to measure execution time
start = time.time()

# ---------------- Simulation Parameters --------------------------------
TICKS = 300             # Number of ticks in the simulation
P0 = 100.0              # Initial price
TICK_SIZE = 0.01        # Price tick size (minimum price movement)

# Noise trader intensities
LAMBDA_NOISE_BUY  = 20  # (20) Intensity of noise buy orders
LAMBDA_NOISE_SELL = 20  # (20) Intensity of noise sell orders

# Trend‑followers
LAMBDA_TF = 10          # (10) Intensity of trend-following orders
TREND_WINDOW = 2        # Number of ticks to determine trend direction

P_MARKET_BUY = 0.8      # (0.6) Probability of executing a market buy order
P_MARKET_SELL = 0.8     # (0.6) Probability of executing a market sell order

MU_VOL_BUY = 10         # Mean volume for noise buy orders
MU_VOL_SELL = 10        # Mean volume for noise sell orders

DELTA = 0.02            # (0.01) Relative price deviation for limit orders
P_CANCEL = 0.025        # (0.025) Probability of cancelling an order at each tick

# MM_SPREAD = 0.003       # (0.003) Market maker spread (relative)
# MM_VOL = 100            # (50) Volume of market maker orders

# ----- inventory-aware MM parameters -----------------------------------
MM_BASE_SPREAD   = 0.003     # baseline relative spread (old MM_SPREAD)
MM_BASE_VOL      = 150       # baseline quoted size   (old MM_VOL)
INV_ALPHA        = 0.00005   # price skew per +1 unit inventory
INV_VOL_BETA     = 0.0004    # volume shrink factor   (per unit inv)
INV_SPREAD_GAMMA = 0.00001   # extra half-spread per |inventory|
INV_MAX          = 5_000     # soft inventory limit   (for scaling)


# ---------------- Helper ------------------------------------------------
def round_price(p): return round(p / TICK_SIZE) * TICK_SIZE

class LimitOrder:
    """
    Represents a limit order in a trading system simulation.
    A limit order specifies the side (buy/sell), price, and volume, and is active from a given start tick.
    Each order is assigned a unique identifier upon creation.
    Attributes:
        id (int): Unique identifier for the order.
        side (str): The side of the order ('buy' or 'sell').
        price (float): The price at which the order is placed.
        volume (float): The quantity of the asset to be traded.
        start_tick (int): The simulation tick when the order becomes active.
        end_tick (int or None): The simulation tick when the order is completed or cancelled.
    """
    _id = 0
    def __init__(self, side, price, volume, start_tick):
        self.id = LimitOrder._id
        LimitOrder._id += 1
        self.side = side
        self.price = price
        self.volume = volume
        self.start_tick = start_tick
        self.end_tick = None
        self.mm_tag = False          # <-- default value

class OrderBook:
    def __init__(self):
        """
        Initializes the market simulation by setting up dictionaries to store bids, asks, and orders.
        Attributes:
            bids (dict): Stores current bid orders.
            asks (dict): Stores current ask orders.
            orders (dict): Stores all orders in the market.
        """
        self.bids = {}
        self.asks = {}
        self.orders = {}
    
    def add_limit(self, order):
        """
        Adds a limit order to the order book.
        This method inserts the given order into the appropriate side of the order book
        (bids for 'buy' orders, asks for 'sell' orders) at the specified price level.
        The order is also tracked in the orders dictionary by its unique ID.
        Args:
            order: An object representing the order to be added. It must have 'side', 'price', and 'id' attributes.
        """
        book = self.bids if order.side == 'buy' else self.asks
        book.setdefault(order.price, []).append(order.id)
        self.orders[order.id] = order
    
    def best_bid(self): 
        """
        Returns the highest bid price from the current list of bids.
        If there are no bids available, returns None.
        Returns:
            float or None: The highest bid price if bids exist, otherwise None.
        """
        return max(self.bids) if self.bids else None
    
    def best_ask(self): 
        """
        Returns the lowest ask price from the current list of asks.
        If there are no asks available, returns None.
        Returns:
            float or None: The lowest ask price, or None if no asks exist.
        """
        return min(self.asks) if self.asks else None
    
    def _consume(self, book, vol, asc, t):
        """
        Consumes volume from an order book, filling orders according to price priority.
        This method iterates through the order book, matching and filling orders until the requested
        volume is consumed or the book is empty. Orders are filled starting from the best price
        (lowest for ascending, highest for descending). As orders are filled, their volume is reduced,
        and fully filled orders are removed from the book and the internal order registry.
        Args:
            book (dict): The order book, mapping price levels to lists of order IDs.
            vol (int): The total volume to consume from the book.
            asc (bool): If True, consume from lowest price upwards; if False, from highest price downwards.
            t (int): The current tick or timestamp, used to record when an order is fully filled.
        Returns:
            int: The total volume filled from the book.
        """
        filled=0
        while vol>0 and book:
            price = min(book) if asc else max(book)
            ids = book[price]
            while ids and vol>0:
                oid=ids[0]
                order=self.orders[oid]
                take=min(vol,order.volume)
                order.volume-=take
                filled+=take
                vol-=take
                if order.volume==0:
                    order.end_tick=t
                    ids.pop(0)
                    del self.orders[oid]
            if not ids: del book[price]
        return filled
    
    def match_market(self, side, vol, t):
        """
        Matches a market order against the order book and consumes available volume.
        Args:
            side (str): The side of the market order, either 'buy' or 'sell'.
            vol (float): The volume of the order to be matched.
            t (Any): The timestamp or contextual information for the order.
        Returns:
            Any: The result of the _consume operation, typically the details of the matched trades.
        Description:
            This method processes a market order by matching it against the best available prices
            on the opposite side of the order book (asks for 'buy', bids for 'sell'). It consumes
            the specified volume and returns the result of the matching process.
        """
        return self._consume(self.asks if side=='buy' else self.bids, vol, True if side=='buy' else False, t)
    
    def cancel_random(self, p, t):
        """
        Randomly cancels a proportion of active orders in the order book.
        Args:
            p (float): The probability with which each order is cancelled (between 0 and 1).
            t (int): The current tick or time step, used to mark the cancellation time for each order.
        Description:
            Iterates through all active orders and, with probability `p`, cancels each order.
            The order is removed from the corresponding side of the order book (bids or asks).
            If the price level becomes empty after removal, it is deleted from the book.
            The order's `end_tick` is set to `t` before removal from the active orders.
        """
        for oid,order in list(self.orders.items()):
            if random.random()<p:
                book=self.bids if order.side=='buy' else self.asks
                book[order.price].remove(oid)
                if not book[order.price]: del book[order.price]
                order.end_tick=t
                del self.orders[oid]
    
    def remove_by_flag(self, flag, t):
        """
        Removes all orders from the order book for which the provided flag function returns True.

        Args:
            flag (Callable[[Order], bool]): A function that takes an order as input and returns True if the order should be removed.
            t (int): The current tick, which will be set as the end_tick for each removed order.

        Description:
            Iterates through all orders in the order book and applies the flag function to each order.
            If the flag returns True for an order, the order is removed from the appropriate side of the book (bids or asks),
            its end_tick is set to the provided tick value, and it is deleted from the internal orders dictionary.
            This method allows for flexible removal of orders based on arbitrary criteria such as volume, age, or custom attributes.
        """
        for oid,order in list(self.orders.items()):
            if flag(order):
                book=self.bids if order.side=='buy' else self.asks
                book[order.price].remove(oid)
                if not book[order.price]: del book[order.price]
                order.end_tick=t
                del self.orders[oid]

def depth_side(order_book, side='bid', levels=5):
    """
    Return [(price, depth)] for the first <levels> price points
    on the chosen side ('bid' or 'ask').
    """
    price_dict = order_book.bids if side == 'bid' else order_book.asks
    reverse    = (side == 'bid')                 # bids: high→low
    out = []
    for price in sorted(price_dict, reverse=reverse)[:levels]:
        depth = sum(order_book.orders[oid].volume    # <-- volume, not vol
                    for oid in price_dict[price])
        out.append((price, depth))
    while len(out) < levels:
        out.append((np.nan, 0))
    return out

# 1.  Hurst-exponent helper (classical R/S)
def hurst_rs(series, min_chunk=10, max_chunks=50):
    """
    Estimate Hurst exponent using full R/S analysis.
    Input: series (1D np.array), length N
    Returns: estimated H
    """
    N = len(series)
    if N < min_chunk * 2:
        return np.nan

    # Define chunk sizes logarithmically spaced
    chunk_sizes = np.unique(np.floor(np.logspace(
        np.log10(min_chunk), np.log10(N // 2), num=max_chunks)).astype(int))
    
    log_n = []
    log_rs = []

    for size in chunk_sizes:
        num_chunks = N // size
        rs_vals = []
        for i in range(num_chunks):
            chunk = series[i*size : (i+1)*size]
            if len(chunk) < size:
                continue
            mean = np.mean(chunk)
            dev = chunk - mean
            Z = np.cumsum(dev)
            R = np.max(Z) - np.min(Z)
            S = np.std(chunk, ddof=1)
            if S > 0:
                rs_vals.append(R / S)
        if len(rs_vals) > 0:
            log_n.append(np.log(size))
            log_rs.append(np.log(np.mean(rs_vals)))

    if len(log_n) < 2:
        return np.nan

    # Fit log(R/S) = H log(n) + C
    H, _ = np.polyfit(log_n, log_rs, 1)
    return H

# ---------------- Run Simulation ---------------------------------------
ob=OrderBook()          # Initialize the order book
mid=P0                  # Initial mid price
price_hist=[P0]*TREND_WINDOW # Price history for trend detection
all_orders=[]           # List to store all orders created during the simulation
ohlc=[]                 # Open-High-Low-Close data
volumes=[]              # Volume data
mm_inv = 0              # market-maker inventory (+ long, – short)
spread_series = []      # To store spread values

depth_bid_series = []   # To store bid depth levels
depth_ask_series = []   # To store ask depth levels

# ------------------------------------------------------------------
# PRE-GENERATE Poisson arrival counts (noise + TF intensity upper bound)
# ------------------------------------------------------------------
noise_buy_arr  = np.random.poisson(LAMBDA_NOISE_BUY,  size=TICKS)
noise_sell_arr = np.random.poisson(LAMBDA_NOISE_SELL, size=TICKS)
tf_raw_arr     = np.random.poisson(LAMBDA_TF,         size=TICKS)  # we’ll mask by trend sign
# ------------------------------------------------------------------

# Main simulation loop
for t in range(TICKS):
    
    # new MM
    # bid=round_price(mid*(1-MM_SPREAD/2)) 
    # ask=round_price(mid*(1+MM_SPREAD/2))
    
    # Remove ALL old MM quotes unconditionally
    ob.remove_by_flag(lambda o: o.start_tick == t - 1 and getattr(o, "mm_tag", False), t )

    # ───  INVENTORY-AWARE MARKET MAKER  ─────────────────────────────────
    half_spread = (MM_BASE_SPREAD + INV_SPREAD_GAMMA * abs(mm_inv)) / 2
    skew        =  INV_ALPHA * mm_inv                     # price shift

    bid_price = round_price(mid * (1 - half_spread) - skew)
    ask_price = round_price(mid * (1 + half_spread) - skew)

    # Quote smaller size on the side that would INCREASE exposure
    scale_bid = max(0.1, 1 - INV_VOL_BETA * max(0,  mm_inv) )
    scale_ask = max(0.1, 1 - INV_VOL_BETA * max(0, -mm_inv) )

    vol_bid = int(MM_BASE_VOL * scale_bid)
    vol_ask = int(MM_BASE_VOL * scale_ask)

    for side, p, v in (('buy', bid_price, vol_bid),
                    ('sell', ask_price, vol_ask)):
        lo = LimitOrder(side, p, v, t)
        lo.mm_tag = True
        ob.add_limit(lo)
        all_orders.append(lo)            # keep if you still plot lifetimes
    # ────────────────────────────────────────────────────────────────────

    
    # trend sign
    sma_now = np.mean(price_hist[-TREND_WINDOW:])
    sma_prev = np.mean(price_hist[:-1][-TREND_WINDOW:])
    trend = np.sign(sma_now - sma_prev)
    
    # noise trader orders
    noise_buy  = noise_buy_arr[t]
    noise_sell = noise_sell_arr[t]

    # trend-follower orders
    tf_draw    = tf_raw_arr[t]
    tf_buy  = tf_draw if trend > 0 else 0
    tf_sell = tf_draw if trend < 0 else 0
     
    # create events
    events=['buy_noise']*noise_buy+['sell_noise']*noise_sell+['buy_tf']*tf_buy+['sell_tf']*tf_sell
    
    random.shuffle(events)  # shuffle events to mix noise and trend-follower orders
    o=h=l=mid               # open price
    m_b = 0                   # filled BUY market orders this tick
    m_s = 0                   # filled SELL market orders this tick
    traded=0                # reset traded volume for this tick

    # process events
    for ev in events:

        filled = 0          # reset filled volume for this order

        if ev.startswith('buy'):    # buy order
            side='buy' 
            vol=max(1,np.random.poisson(MU_VOL_BUY))
            pmkt=P_MARKET_BUY
            limit_p=round_price(mid*(1-random.uniform(0,DELTA)))
        else:                       # sell order
            side='sell'
            vol=max(1,np.random.poisson(MU_VOL_SELL))
            pmkt=P_MARKET_SELL
            limit_p=round_price(mid*(1+random.uniform(0,DELTA)))
        
        if random.random()<pmkt:    # market order
            filled = ob.match_market(side, vol, t)   # ONE call only
            traded += filled
            if filled > 0:                  # count only if something traded
                if side == 'buy':
                    m_b += 1
                    mm_inv -= filled
                else:
                    m_s += 1
                    mm_inv += filled
        else:                       # limit order
            lo = LimitOrder(side, limit_p, vol, t)
            ob.add_limit(lo)
            all_orders.append(lo)
        
        mm_inv = np.clip(mm_inv, -INV_MAX, INV_MAX) # soft limit on MM inventory

         # ── PRICE UPDATE (quote driven) ─────────────────────────────
        best_bid = ob.best_bid()
        best_ask = ob.best_ask()

        if best_bid is not None and best_ask is not None:
            mid = (best_bid + best_ask) / 2          # classic mid-price
        elif best_bid is not None:
            mid = best_bid                           # only bid side left
        elif best_ask is not None:
            mid = best_ask                           # only ask side left
        # else: keep previous mid if both sides empty

        # update high/low for this bar
        h = max(h, mid)
        l = min(l, mid)
    
    # ----- after processing all events in a bar ------------------
    best_bid = ob.best_bid()
    best_ask = ob.best_ask()
    if best_bid is not None and best_ask is not None:
        spread_series.append(best_ask - best_bid)
    else:
        spread_series.append(np.nan)

    # ---- RECORD DEPTH LEVELS ------------------------------------------------

    depth_bid = depth_side(ob, side='bid', levels=5)
    depth_ask = depth_side(ob, side='ask', levels=5)

    # Store only the volumes for lighter plotting later
    depth_bid_series.append([d[1] for d in depth_bid])
    depth_ask_series.append([d[1] for d in depth_ask])
    
    ob.cancel_random(P_CANCEL,t)    # cancel random orders
    c=mid                           # close price is the mid price
    ohlc.append((o,h,l,c))          # record OHLC data
    volumes.append(traded)          # record OHLC data and volume
    price_hist.append(c)            # update price history
    price_hist=price_hist[-TREND_WINDOW:] # keep only the last TREND_WINDOW prices

# Convert depth lists to arrays  (shape: ticks × 5)
bid_mat = np.array(depth_bid_series)    # volumes, no prices needed now
ask_mat = np.array(depth_ask_series)

# Convert spread series to a numpy array
spreads = np.array(spread_series)

# --- Weighted depth (liquidity) ----------------------------------------
weights = 1 / (np.arange(1, 6))                     # 1, 1/2, … 1/5
liq_bid = (bid_mat * weights).sum(axis=1)
liq_ask = (ask_mat * weights).sum(axis=1)
liquidity = liq_bid + liq_ask                       # symmetric liquidity measure

# --- Slope-adjusted liquidity (simple linear fit) ----------------------
# Fit volume vs level index for bid and ask separately
x_levels = np.arange(1, 6)
slope_bid = -np.apply_along_axis(
    lambda y: np.polyfit(x_levels, y, 1)[0], 1, bid_mat)
slope_ask =  np.apply_along_axis(
    lambda y: np.polyfit(x_levels, y, 1)[0], 1, ask_mat)

slope_combined = (slope_bid + slope_ask) / 2     # shape (TICKS,)

resilience_times = np.full(TICKS, np.nan)
thresh = 0.9

for t in range(1, TICKS):
    if liquidity[t] < thresh * liquidity[t-1]:          # liquidity shock
        baseline = liquidity[t-1]
        for τ in range(1, min(100, TICKS - t)):         # 100-tick cap
            if liquidity[t+τ] >= thresh * baseline:
                resilience_times[t] = τ
                break


for order in all_orders:                            # ensure all orders have an end_tick
    if order.end_tick is None: order.end_tick=TICKS

close_prices=np.array([c for (_,_,_,c) in ohlc])    # Close prices for the spectrum analysis

# -------------------------------------------------------------------

# 2.  Rolling-window Hurst calculation
WINDOW = 100
hurst_values = np.full_like(close_prices, np.nan, dtype=float)
for idx in range(WINDOW, len(close_prices) + 1):
    segment = close_prices[idx - WINDOW: idx]
    hurst_values[idx - 1] = hurst_rs(segment, min_chunk=20, max_chunks=WINDOW)
# -------------------------------------------------------------------

# Spectrum (period vs power)
# -- Use the previous `close_prices` array (`close_prices` comes from the prior cell) --
N = len(close_prices)

# Apply Hamming window
window = np.hamming(N)
signal = (close_prices - close_prices.mean()) * window

# FFT
fft_vals = np.fft.rfft(signal)
freqs = np.fft.rfftfreq(N, d=1)      # cycles per tick
power = np.abs(fft_vals)**2

# Convert to dB, normalising to the maximum power in the band
power_db = 10 * np.log10(power / power.max())

# A csv output of the frequencies and their corresponding power
# This is useful for debugging or further analysis
np.savetxt("spectrum.csv", np.column_stack((freqs, power)), delimiter=",", header="Frequency,Power", comments='')

# Filter out zero or near-zero frequencies to avoid log(0)
valid = freqs > 0
log_f = np.log10(freqs[valid])
log_p = np.log10(power[valid])

# Linear fit in log-log space
coeffs = np.polyfit(log_f, log_p, 1)
alpha, log_c = coeffs
fitted_log_p = np.polyval(coeffs, log_f)
fitted_power = 10 ** fitted_log_p
fitted_db = 10 * np.log10(fitted_power / fitted_power.max())

# Estimate Hurst coefficient from alpha
hurst_exponent = -(alpha + 1) / 2

# Calculate fall off in power per octave based on alpha
fall_off = np.diff(fitted_db) / np.diff(log_f)

# End timer before plotting
end = time.time()
print(f"Elapsed time: {end - start:.2f} seconds")

# --- Plotting switch ---
ENABLE_PLOTTING = True  # Set to False to disable all plotting

if not ENABLE_PLOTTING:
    exit(0)

# ─────────────────────────  PLOTTING  ────────────────────────────────
# Create a figure with subplots for different visualizations

# ─────────────────────────  FIGURE 1  ──────────────────────────────
fig1, (ax_price, ax_depth, ax_liq, ax_vol) = plt.subplots(
        4, 1, figsize=(12, 10),
        sharex=False,
        gridspec_kw={'height_ratios': [2, 1, 1, 1]})

# --- Price panel -------------------------------------------------------
for order in all_orders:
    ax_price.hlines(order.price, order.start_tick, order.end_tick,
                    color='blue' if order.side == 'buy' else 'red',
                    alpha=0.15 + 0.65 * min(order.volume, 50)/50,
                    lw=0.4)

w = 0.6
for i, (o_, h_, l_, c_) in enumerate(ohlc):
    col = 'green' if c_ >= o_ else 'black'
    ax_price.vlines(i, l_, h_, color=col, lw=1)
    if c_ == o_:
        ax_price.hlines(o_, i-w/2, i+w/2, color=col, lw=1.2)
    else:
        ax_price.add_patch(
            plt.Rectangle((i-w/2, min(o_, c_)), w, abs(c_-o_),
                          color=col, alpha=0.8))
ax_price.set_ylabel("Price")

# --- Depth heat-map (L1–L5) with inset colour-bar ----------------------
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

depth_img = np.vstack([bid_mat, ask_mat])

im = ax_depth.imshow(
        depth_img.T,
        aspect='auto',
        extent=[0, TICKS, 1, 5],
        origin='lower',
        cmap='Blues')

ax_depth.set_ylabel("Level")
ax_depth.set_title("Bid (left) & Ask (right) Depth (L1–L5)")

# → inset colour-bar occupies 4 % of axis width, 90 % of height
cax = inset_axes(ax_depth,
                 width="4%", height="90%",
                 loc='lower right',
                 bbox_to_anchor=(0.02, 0.0, 1, 1),  # x-offset, y-offset, w, h (rel to ax)
                 bbox_transform=ax_depth.transAxes,
                 borderpad=0)

plt.colorbar(im, cax=cax, orientation='vertical', label="Volume")
cax.yaxis.set_label_position('left')   # put label on left of bar
cax.yaxis.tick_left()


# --- Liquidity + resilience -------------------------------------------
ax_liq.plot(liquidity, label="Weighted Liquidity", color='teal')
ax_liq2 = ax_liq.twinx()
ax_liq2.plot(resilience_times, label="Resilience τ", color='firebrick')
ax_liq.set_ylabel("Liquidity")
ax_liq2.set_ylabel("Recovery ticks")
ax_liq.legend(loc='upper left'); ax_liq2.legend(loc='upper right')

# --- Volume bar plot ---------------------------------------------------
ax_vol.bar(range(TICKS), volumes, color='orange')
ax_vol.set_ylabel("Volume")
ax_vol.set_xlabel("Tick")

fig1.suptitle("Price / Depth / Liquidity / Volume")
fig1.tight_layout()

# ─────────────────────────  FIGURE 2  ──────────────────────────────
fig2, (ax_hurst, ax_spec) = plt.subplots(
        2, 1, figsize=(10, 6),
        sharex=False,
        gridspec_kw={'height_ratios': [1, 2]})

# --- Rolling Hurst exponent -------------------------------------------
ax_hurst.plot(range(TICKS), hurst_values, color='purple', alpha=0.9)
ax_hurst.axhline(0.5, ls='--', color='grey', lw=0.8)
ax_hurst.set_ylim(0, 1.5)
ax_hurst.set_ylabel("Hurst $H$")
ax_hurst.set_title(f"Rolling Hurst (window={WINDOW})")

# --- Power spectrum + log-log fit -------------------------------------
ax_spec.plot(freqs[valid], power_db[valid], label="Power (dB)")
ax_spec.plot(freqs[valid], fitted_db, 'r--',
             label=f"Fit: α={alpha:.2f}, H={hurst_exponent:.2f}")
ax_spec.set_xscale('log')
ax_spec.set_xlabel("Frequency (cycles per tick)")
ax_spec.set_ylabel("Power (dB)")
ax_spec.legend()
ax_spec.set_title("Log–Log Spectrum & Linear Fit")

fig2.tight_layout()

# --- Show BOTH figures -------------------------------------------------
plt.show(block=False)   # keep first window
plt.show()              # show second; both stay open
