import backtrader as bt

def build_strategy_class(strategy_json):
    """
    Dynamically create and return a Backtrader Strategy class
    based on the provided AI-generated JSON.
    """
    # Extract top-level fields
    strategy_name = strategy_json.get("strategy_name", "AI_Generated_Strategy")
    entry_logic  = strategy_json.get("entry_logic", {})
    exit_logic   = strategy_json.get("exit_logic", {})
    risk_mgmt    = strategy_json.get("risk_management", {})

    # Extract indicator definitions
    stop_loss = risk_mgmt.get("stop_loss", None)      # e.g. 5 -> 5%
    take_profit = risk_mgmt.get("take_profit", None)  # e.g. 10 -> 10%
    position_size = risk_mgmt.get("position_size", 1) # e.g. 10 (shares) or 0.05 (5% of capital)

    # For convenience, store them at function scope
    entry_operator = entry_logic.get("operator", "all") 
    exit_operator  = exit_logic.get("operator", "all")

    # Condition arrays
    entry_conditions = entry_logic.get("conditions", [])
    exit_conditions  = exit_logic.get("conditions", [])
    
    
    # Mapping for known indicators
    _INDICATOR_MAP = {
    # Moving Averages
    "SMA": bt.ind.SmoothedMovingAverage,                            # Simple Moving Average
    "EMA": bt.ind.ExponentialMovingAverage,                            # Exponential Moving Average
    "WMA": bt.ind.WeightedMovingAverage,                            # Weighted Moving Average
    "DEMA": bt.ind.DoubleExponentialMovingAverage,                          # Double Exponential Moving Average
    "TEMA": bt.ind.TripleExponentialMovingAverage,                          # Triple Exponential Moving Average
    "SMMA": bt.ind.SmoothedMovingAverage,         # Smoothed Moving Average
    "HMA": bt.ind.HullMovingAverage,              # Hull Moving Average
    # "KAMA": bt.ind.kama,                          # Kaufman Adaptive Moving Average
    "ZLEMA": bt.ind.ZeroLagExponentialMovingAverage,                   # Zero-Lag Exponential Moving Average (alias works)

    # Momentum / Oscillators
    "RSI": bt.ind.RelativeStrengthIndex,
    "MACD": bt.ind.MACD,
    "STOCH": bt.ind.Stochastic,
    "MOMENTUM": bt.ind.Momentum,
    "ROC": bt.ind.RateOfChange,                            # Rate of Change
    "TRIX": bt.ind.Trix,
    "CCI": bt.ind.CommodityChannelIndex,                            # Commodity Channel Index
    "UO": bt.ind.UltimateOscillator,              # Ultimate Oscillator
    "AO": bt.ind.AwesomeOscillator,               # Awesome Oscillator
    "PPO": bt.ind.PercentagePriceOscillator,                            # Percentage Price Oscillator
    # "RVI": bt.ind.RVI,  # REMOVED: Not in standard Backtrader
    "CCI": bt.ind.CommodityChannelIndex,                            # Commodity Channel Index

    # Volatility / Range
    "ATR": bt.ind.AverageTrueRange,                            # Average True Range
    "BOLLINGER": bt.ind.BollingerBands,           # Bollinger Bands
    "BBANDS": bt.ind.BollingerBands,              # Same class, “BBands” alias
    # "NATR": bt.ind.ATR,                          # Normalized ATR

    # Trend / Direction
    "ADX": bt.ind.AverageDirectionalMovementIndex,  # Average Directional Movement Index
    "ADXR": bt.ind.AverageDirectionalMovementIndexRating,   # Average Directional Movement Index Rating
    "PLUS_DI": bt.ind.PlusDirectionalIndicator,                    # +DI
    "MINUS_DI": bt.ind.MinusDirectionalIndicator,                  # –DI
    #"PLUS_DM": bt.ind.PLUS_DM,                    # +DM
    #"MINUS_DM": bt.ind.MINUS_DM,                  # –DM
    "SAR": bt.ind.ParabolicSAR,                   # Parabolic SAR

    # Volume-based
    # "OBV": bt.ind.obv,                            # On Balance Volume
    # "MFI": bt.ind.MFI,                            # Money Flow Index

    # Other
    # “Aroon” doesn’t exist alone → renamed to AroonUpDown / AroonOscillator
    "AROONUPDOWN": bt.ind.AroonUpDown,            # Replaces "AROON"
    "AROONOSC": bt.ind.AroonOscillator,           # Replaces "AROONOSC"
    "HEIKINASHI": bt.ind.HeikinAshi,
    "ICHIMOKU": bt.ind.Ichimoku,                  # Ichimoku Kinko Hyo
    # "HOLP": bt.ind.HOLP,                          # Highest Open/Low Period
    # "LOLP": bt.ind.LOLP                           # Lowest Open/Low Period
    }

    # ============ 1) Create an inner class that extends bt.Strategy ===========
    class AIConstructedStrategy(bt.Strategy):
        """
        Dynamically constructed strategy from JSON.
        """
       
        def __init__(self):
            # We’ll store built indicator info in these
            self.entry_conds = []
            self.exit_conds  = []
            # We'll store all created indicators in a list for easy logging:
            self.all_indicators = []

            # 1) Build all indicators from the JSON
            for cdef in entry_conditions:
                ind_type = cdef.get("type", "RSI").upper()
                params   = cdef.get("parameters", {})
              
                 # --- NEW: Remap for MACD ---
                if ind_type == "MACD":
                    if "fastperiod" in params:
                        params["period_me1"] = params.pop("fastperiod")
                    if "slowperiod" in params:
                        params["period_me2"] = params.pop("slowperiod")
                    if "signalperiod" in params:
                        params["period_signal"] = params.pop("signalperiod")

                # Get the main indicator class
                main_class = _INDICATOR_MAP.get(ind_type, bt.ind.RSI)  # default to RSI if unknown
                main_inst = main_class(self.data, **params)

                # We also store a reference name, e.g. "entry0_RSI"
                ind_name = f"entry{len(self.entry_conds)}_{ind_type}"
                # Keep track so we can reference it in next()
                self.all_indicators.append((ind_name, main_inst))

                # Build reference if any
                ref_inst = None
                ref_type = cdef.get("reference", None)        # e.g. "PRICE", "SignalLine", "SMA"
                ref_params = cdef.get("reference_parameters", {})

                if ref_type:
                    ref_inst = self._resolve_reference_line(ind_type, main_inst, ref_type)
                    if ref_inst is None:
                        # fallback to second indicator instance if valid
                        rtype = ref_type.upper()
                        ref_class = _INDICATOR_MAP.get(rtype)
                        if ref_class:
                            if rtype == "MACD":
                                if "fastperiod" in ref_params:
                                    ref_params["period_me1"] = ref_params.pop("fastperiod")
                                if "slowperiod" in ref_params:
                                    ref_params["period_me2"] = ref_params.pop("slowperiod")
                                if "signalperiod" in ref_params:
                                    ref_params["period_signal"] = ref_params.pop("signalperiod")
                            ref_inst = ref_class(self.data, **ref_params)
                        else:
                            if self.debug:
                                self.log(f"[WARN] Unknown reference '{ref_type}' for {ind_type}. Using close price as fallback.")
                            ref_inst = self.data.close

                # **Append** the built item to self.entry_conds
                self.entry_conds.append({
                    "condition": cdef["condition"],
                    "value": cdef.get("value"),
                    "description": f"{ind_type} {cdef['condition']} {cdef.get('value')}",  
                    "_main_inst": main_inst,
                    "_ref_inst": ref_inst
                })

            # 2) For exit condition, build an exit indicator if needed
            for cdef in exit_conditions:
                ind_type = cdef.get("type", "RSI").upper()
                params   = cdef.get("parameters", {})

                 # --- NEW: Remap for MACD ---
                if ind_type == "MACD":
                    if "fastperiod" in params:
                        params["period_me1"] = params.pop("fastperiod")
                    if "slowperiod" in params:
                        params["period_me2"] = params.pop("slowperiod")
                    if "signalperiod" in params:
                        params["period_signal"] = params.pop("signalperiod")

                main_class = _INDICATOR_MAP.get(ind_type, bt.ind.RSI)
                main_inst  = main_class(self.data, **params)
            
                ind_name = f"exit{len(self.exit_conds)}_{ind_type}"
                self.all_indicators.append((ind_name, main_inst))

                 # Build reference if any
                ref_inst = None
                ref_type = cdef.get("reference", None)
                ref_params = cdef.get("reference_parameters", {})
                if ref_type:
                    if ref_type == "PRICE":
                        ref_inst = self.data.close
                    elif ref_type == "SignalLine" and ind_type in ["MACD", "PPO"]:
                        ref_inst = main_inst.signal
                    else:
                        rtype = ref_type.upper()
                        ref_class = _INDICATOR_MAP.get(rtype)
                        if ref_class:
                            if rtype == "MACD":
                                if "fastperiod" in ref_params:
                                    ref_params["period_me1"] = ref_params.pop("fastperiod")
                                if "slowperiod" in ref_params:
                                    ref_params["period_me2"] = ref_params.pop("slowperiod")
                                if "signalperiod" in ref_params:
                                    ref_params["period_signal"] = ref_params.pop("signalperiod")
                            ref_inst = ref_class(self.data, **ref_params)
                        else:
                            ref_inst = self.data.close

                self.exit_conds.append({
                    "condition": cdef["condition"],
                    "value": cdef.get("value"),
                    "description": f"{ind_type} {cdef['condition']} {cdef.get('value')}",  
                    "_main_inst": main_inst,
                    "_ref_inst": ref_inst
                })

            # Store the operator strings
            self.entry_operator = entry_operator
            self.exit_operator  = exit_operator

            # Risk mgmt
            self.stop_loss     = stop_loss
            self.take_profit   = take_profit
            self.position_size = position_size
         
            # We'll store bar-by-bar logs here:
            self.debug = False  # Set this to True if you want verbose output
            self.daily_logs = []
         
            # Done with __init__
         
        def _resolve_reference_line(self, ind_type, main_inst, ref_type):
            """
            Maps reference strings like 'SignalLine', 'LowerBand', etc. to indicator lines.
            """
            if ref_type == "PRICE":
                return self.data.close
            if ref_type == "SignalLine" and ind_type in ["MACD", "PPO"]:
                return main_inst.signal
            if ind_type == "STOCH":
                if ref_type == "SignalLine":
                    return main_inst.percD()
                elif ref_type == "percK":
                    return main_inst.percK()
            if ind_type in ["BOLLINGER", "BBANDS"]:
                if ref_type == "LowerBand":
                    return main_inst.bot
                elif ref_type == "UpperBand":
                    return main_inst.top
                elif ref_type == "MiddleBand":
                    return main_inst.mid
            if ind_type == "AROONUPDOWN":
                if ref_type == "AROONDOWN":
                    return main_inst.down
                elif ref_type == "AROONUP":
                    return main_inst.up
            if ind_type == "ICHIMOKU":
                if ref_type == "SenkouA":
                    return main_inst.senkou_span_a
                elif ref_type == "SenkouB":
                    return main_inst.senkou_span_b
                elif ref_type == "Tenkan":
                    return main_inst.tenkan
                elif ref_type == "Kijun":
                    return main_inst.kijun
            return None  # fallback to None if not found
 
            
        def _check_cross_condition(self, main_line, ref_line, cross_type):
            """
            Returns True if a cross_above/cross_below happened between main_line and ref_line
            on this bar (comparing previous bar).
            """
            if ref_line is None:
                # If we have no reference, we might interpret cross with '0' line
                # but let's assume we want cross with zero
                ref_line = [0.0, 0.0]

            # Yesterday (bar -1) vs today (bar 0)
            # Use bracket indexing to get a single bar’s float value
            prev_main = main_line[-1]
            prev_ref  = ref_line[-1]
            curr_main = main_line[0]
            curr_ref  = ref_line[0]

            if cross_type == "cross_above":
                # check if prev_main < prev_ref and curr_main > curr_ref
                return (prev_main < prev_ref) and (curr_main > curr_ref)
            elif cross_type == "cross_below":
                return (prev_main > prev_ref) and (curr_main < curr_ref)
            return False

        def _check_indicator_signal(self, cdef):
            """
            Evaluate one indicator's condition: e.g. RSI < 30 => True/False
            or a cross condition => cross_above, cross_below
            """
            condition = cdef["condition"]   # e.g. "<"
            val  = cdef["value"]       # e.g. 30
            main_inst = cdef["_main_inst"]
            ref_inst  = cdef["_ref_inst"]

            if condition in ("cross_above", "cross_below"):
                # We check if main_inst crosses above/below ref_inst or zero
                if ref_inst is not None:
                    return self._check_cross_condition(main_inst, ref_inst, condition)
                else:
                    # If ref is None but user said cross, we might treat val as zero line
                    zero_line = [0.0, 0.0]  # hacky
                    return self._check_cross_condition(main_inst, zero_line, condition)

            else:
                # e.g. <, >, <=, >=
                current_val = main_inst[0]
                if condition == "<" and val is not None:
                    return (current_val < val)
                elif condition == ">" and val is not None:
                    return (current_val > val)
                elif condition == "<=" and val is not None:
                    return (current_val <= val)
                elif condition == ">=" and val is not None:
                    return (current_val >= val)

            # Otherwise default to False
            return False
        
        def log(self, txt, dt=None):
            """ Logging function """
            if self.debug:
                dt = dt or self.datas[0].datetime.date(0)
                print(f'{dt.isoformat()} {txt}')

        def next_open(self):
            
            # Evaluate entry conditions => True or False
            entry_signals = []
            for e in self.entry_conds:
                # We’ll do a small helper
                esig = self._check_indicator_signal(e)
                entry_signals.append(esig)

            # Combine them with "any" or "all"
            if self.entry_operator == "all":
                entry_signal = all(entry_signals)
            else:
                entry_signal = any(entry_signals)

            # Evaluate exit similarly
            exit_signals = []
            for e in self.exit_conds:
                xsig = self._check_indicator_signal(e)
                exit_signals.append(xsig)

            if self.exit_operator == "all":
                exit_signal = all(exit_signals)
            else:
                exit_signal = any(exit_signals)

            # Prepare variables to capture trade action and risk info
            trade_action = "NONE"      # Will be set to BUY, SELL, or HOLD
            trade_reason = ""
            risk_info = {}
            order_details = {}         # To store the returned order attributes
            order = None               # To capture the order object

            # 4) Trading logic
            if not self.position:
                if entry_signal:
                    # print statement for debugging including the entry signal
                    trade_action = "BUY"
                    trade_reason = "Entry conditions met: " + ", ".join(str(s) for s in entry_signals)
                    if self.debug:
                        self.log(f"BUY SIGNAL: {entry_signal} | Conditions: {entry_signals}")
                    # interpret position_size as fraction of capital or fixed shares
                    if self.position_size <= 1:
                        # fraction of capital
                        cash = self.broker.getvalue()
                        shares = int((cash * self.position_size) / self.data.close[0]) - 1 # to avoid trade being rejected
                        if shares > 0:
                            trade_action = "BUY. Shares: " + str(shares)
                            if self.debug:
                                self.log(f"BUYING {shares} shares at {self.data.close[0]:.2f} with {cash:.2f} cash")
                            order = self.buy(size=shares)
                    else:
                        # fixed shares
                        trade_action = "BUY. Size: " + str(self.position_size)
                        if self.debug:
                            self.log(f"BUYING {self.position_size} shares at {self.data.close[0]:.2f}")
                        order = self.buy(size=int(self.position_size))
                        
                else:
                    trade_action = "NO_TRADE"
                    trade_reason = "Entry conditions not met: " + ", ".join(str(s) for s in entry_signals)
            else:
                if exit_signal:
                    trade_action = "SELL"
                    trade_reason = "Exit conditions met: " + ", ".join(str(s) for s in exit_signals)
                    if self.debug:
                        self.log(f"SELL SIGNAL: {exit_signal} | Conditions: {exit_signals}")
                    order = self.close()
                else:
                    trade_action = "HOLD"
                    trade_reason = "Holding position; exit conditions: " + ", ".join(str(s) for s in exit_signals)

            # 5) Risk mgmt
            if self.position.size > 0:
                entry_price = self.position.price
                current_price = self.data.close[0]

                # Stop Loss
                if self.stop_loss:
                    # e.g. 5 => 5% below entry
                    stop_thr = entry_price * (1 - self.stop_loss/100.0)
                    if current_price < stop_thr:
                        risk_info["stop_loss"] = f"Triggered: {current_price:.2f} < {stop_thr:.2f}"
                        trade_action = "SELL"
                        trade_reason = "Stop loss hit"
                        if self.debug:
                            self.log(f"STOP LOSS HIT, Price: {current_price:.2f}")
                        order = self.close()

                # Take Profit
                if self.take_profit:
                    # e.g. 10 => 10% above entry
                    tp_thr = entry_price * (1 + self.take_profit/100.0)
                    if current_price > tp_thr:
                        risk_info["take_profit"] = f"Triggered: {current_price:.2f} > {tp_thr:.2f}"
                        trade_action = "SELL"
                        trade_reason = "Take profit hit"
                        if self.debug: 
                            self.log(f"TAKE PROFIT HIT, Price: {current_price:.2f}")
                        order = self.close()

            # # Get current date and close price
            dt = self.data.datetime.date(0)
            close_price = self.data.close[0]

            # Grabbing each indicator’s current value:
            indicator_values = {}
            for (ind_name, ind_inst) in self.all_indicators:
                # Each indicator is a line that you can read with [0]
                indicator_values[ind_name] = float(ind_inst[0])

            # Current position size, e.g. 0 if flat
            pos_size = self.position.size
            
            # Capture order details if an order was submitted:
            if order is not None:
                order_details = {
                    "order_size": order.size,
                    "order_price": order.price,
                    "order_valid": order.valid,
                    "order_status": order.status
                }
            else:
                order_details = {}


            entry_conditions_main = [float(cond["_main_inst"][0]) for cond in self.entry_conds]
            entry_conditions_ref = [float(cond["_ref_inst"][0]) if cond["_ref_inst"] is not None else None 
                                    for cond in self.entry_conds]
            exit_conditions_main = [float(cond["_main_inst"][0]) for cond in self.exit_conds]
            exit_conditions_ref = [float(cond["_ref_inst"][0]) if cond["_ref_inst"] is not None else None 
                                for cond in self.exit_conds]

            # Build a textual list of each entry condition
            entry_condition_texts = []
            exit_condition_texts = []
            for idx, e in enumerate(self.entry_conds):
                # e["description"] might look like "MACD cross_above None"
                # or you can format it in more detail
                entry_condition_texts.append(e["description"])
            for idx, e in enumerate(self.exit_conds):
                # e["description"] might look like "MACD cross_above None"
                # or you can format it in more detail
                exit_condition_texts.append(e["description"])

            # Build a daily log dictionary with all debugging info
            daily_dict = {
                "date": dt.isoformat(),
                "close": float(close_price),
                "position_size": pos_size,
                "entry_signals": entry_signals,
                "exit_signals": exit_signals,
                "trade_action": trade_action,
                "trade_reason": trade_reason,
                "risk_info": risk_info,
                "order_details": order_details,
                "entry_conditions_main": entry_conditions_main,
                "entry_conditions_ref": entry_conditions_ref,
                "exit_conditions_main": exit_conditions_main,
                "exit_conditions_ref": exit_conditions_ref,
                "entry_conditions": entry_condition_texts,
                "exit_conditions": exit_condition_texts
            }
      
            # Merge in all your indicators:
            daily_dict.update(indicator_values)

            # Append to your daily_logs
            self.daily_logs.append(daily_dict)

        # Notify when an order is completed or rejected
        def notify_order(self, order):
            if order.status in [order.Completed]:
                if order.isbuy():
                    self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size}")
                elif order.issell():
                    self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size}")
            elif order.status in [order.Rejected, order.Margin]:
                self.log(f"ORDER REJECTED OR MARGIN ISSUE: {order.status}")

        def stop(self):
                """
                Once the strategy ends, store daily_logs in an attribute so that
                your backtest engine can fetch it from the final Strategy object.
                """
                self._final_logs = self.daily_logs
                # Alternatively, do any final cleanup or calculations here.

        # def notify_order(self, order):
        #     if order.status in [order.Completed]:
        #         if order.isbuy():
        #             self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}")
        #         else:  # Sell
        #             self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}")

        # def notify_trade(self, trade):
        #     if trade.isclosed:
        #         self.log(f"TRADE PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")


    AIConstructedStrategy.__name__ = f"AI_{strategy_name.replace(' ', '_')}"
    return AIConstructedStrategy
