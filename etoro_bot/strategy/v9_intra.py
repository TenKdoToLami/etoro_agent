"""
Genome V9 Confidence Intra-Day Strategy.
Enhanced version of V9 that looks at the current day's price change (Mid-Price vs Prev Close)
to make same-day trading decisions.
"""

import numpy as np
from .indicators import (
    sma, ema, rsi, macd, adx, atr, trix, linear_regression_slope, realized_volatility, mfi, bollinger_bands
)

class GenomeV9Intra:
    NAME = "Genome V9 (Intra-Day Confidence)"
    version = 9.1
    IS_INTRA = True # Signal to the runner to execute same-day

    def __init__(self, genome=None):
        self.genome = genome or self._default_genome()
        self.reset()
        
        # Pre-cache layers
        w1_raw = np.array(self.genome['layers'][0]['w'])
        
        # AUTOMATIC ADAPTATION: If we are seeding from a 13-input V9 genome
        # we need to expand the weights to 14 inputs.
        if w1_raw.shape[0] == 13:
            # Add a 14th row (the new Intraday Trigger) initialized to 0.0
            # so it doesn't disrupt the existing logic until evolved.
            new_row = np.zeros((1, w1_raw.shape[1]))
            self.w1 = np.vstack([w1_raw, new_row])
        else:
            self.w1 = w1_raw
            
        self.b1 = np.array(self.genome['layers'][0]['b'])
        self.w2 = np.array(self.genome['layers'][1]['w'])
        self.b2 = np.array(self.genome['layers'][1]['b'])
        
        self.state_map = {
            0: {"CASH": 1.0},
            1: {"SPY": 1.0},
            2: {"2xSPY": 1.0},
            3: {"3xSPY": 1.0}
        }

    def _default_genome(self):
        # 14 Inputs (13 + Today's Delta) -> 24 Hidden -> 4 Outputs
        return {
            'version': 9.1,
            'layers': [
                {
                    'w': np.random.uniform(-1, 1, (14, 24)).tolist(),
                    'b': np.zeros(24).tolist()
                },
                {
                    'w': np.random.uniform(-1, 1, (24, 4)).tolist(),
                    'b': np.zeros(4).tolist()
                }
            ],
            'lookbacks': {
                'sma': 200, 'ema': 50, 'rsi': 14, 'macd_f': 12, 'macd_s': 26,
                'adx': 14, 'trix': 15, 'slope': 20, 'vol': 20, 'atr': 14,
                'mfi': 14, 'bb': 20
            },
            'hysteresis': 0.15,
            'smoothing': 0.5
        }

    def reset(self):
        self.prices = []
        self.highs = []
        self.lows = []
        self.volumes = []
        self.prev_ema = None
        self.prev_atr = None
        self.indicator_state = {}
        
        self.current_state_idx = 0
        self.current_holdings = {"CASH": 1.0}
        self.smoothed_scores = np.zeros(4)

    def _softmax(self, x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    def _relu(self, x):
        return np.maximum(0, x)

    def on_data(self, date, price_data, prev_data):
        # In Intra mode, price_data contains the mid-day price at the time of execution
        spy_mid = price_data['close'] # In runner.py mid-price is passed as 'close'
        
        # But we need a history. We'll use the price_data as an "unclosed" candle.
            
        if not self.prices:
            # First day initialization
            self.prices.append(spy_mid)
            self.highs.append(price_data['high'])
            self.lows.append(price_data['low'])
            self.volumes.append(price_data.get('volume', 0))
            return self.current_holdings, {}

        # The 'True' close of yesterday
        prev_close = self.prices[-1]
        
        # 1. Indicators (Using Yesterday's data as the last point)
        lb = self.genome['lookbacks']
        val_sma = sma(self.prices, lb['sma'])
        
        val_ema = ema(self.prices, lb['ema'], prev_ema=self.prev_ema)
        self.prev_ema = val_ema
        
        val_rsi = rsi(self.prices, lb['rsi'], state=self.indicator_state)
        val_macd_tuple = macd(self.prices, lb['macd_f'], lb['macd_s'], state=self.indicator_state)
        val_macd = val_macd_tuple[0] if val_macd_tuple[0] is not None else 0.0
        val_adx = adx(self.highs, self.lows, self.prices, lb['adx'], state=self.indicator_state)
        val_trix = trix(self.prices, lb['trix'], state=self.indicator_state)
        val_slope = linear_regression_slope(self.prices, lb['slope'])
        val_vol = realized_volatility(self.prices, lb['vol'])
        
        val_atr = atr(self.highs, self.lows, self.prices, lb['atr'], prev_atr=self.prev_atr)
        self.prev_atr = val_atr
        
        val_mfi = mfi(self.highs, self.lows, self.prices, self.volumes, lb['mfi'])
        bb_res = bollinger_bands(self.prices, lb['bb'])
        val_bbw = (bb_res[0] - bb_res[2]) / bb_res[1] if bb_res[1] else 0.0

        # 2. Normalize Inputs
        macro_vix = float(price_data.get('vix', 15.0))
        macro_yc = float(price_data.get('yield_curve', 0.0))
        
        # THE 14TH FEATURE: Intraday Return
        intra_ret = (spy_mid - prev_close) / prev_close
        
        inputs = np.array([
            ((spy_mid - val_sma) / val_sma * 5) if val_sma else 0.0,
            ((spy_mid - val_ema) / val_ema * 10) if val_ema else 0.0,
            ((val_rsi or 50) - 50) / 50.0,
            val_macd / spy_mid * 100,
            ((val_adx or 25) - 25) / 25.0,
            val_trix or 0.0,
            (val_slope or 0.0) / spy_mid * 1000,
            (val_vol or 0.15) * 5,
            ((val_atr or 0.0) / spy_mid) * 50,
            (macro_vix - 20) / 10.0,
            macro_yc,
            ((val_mfi or 50) - 50) / 50.0,
            val_bbw * 10,
            intra_ret * 20 # Scaled intraday return
        ])

        # 3. Neural Inference
        h1 = self._relu(np.dot(inputs, self.w1) + self.b1)
        raw_scores = np.dot(h1, self.w2) + self.b2
        probs = self._softmax(raw_scores)
        
        # Update smoothed scores
        alpha = self.genome.get('smoothing', 0.5)
        self.smoothed_scores = alpha * probs + (1 - alpha) * self.smoothed_scores
        
        # Decision
        best_state_idx = np.argmax(self.smoothed_scores)
        current_conf = self.smoothed_scores[self.current_state_idx]
        best_conf = self.smoothed_scores[best_state_idx]
        hysteresis = self.genome.get('hysteresis', 0.15)

        if best_state_idx != self.current_state_idx:
            if best_conf > current_conf + hysteresis:
                self.current_state_idx = best_state_idx
                self.current_holdings = self.state_map[best_state_idx]

        # 4. Prepare Telemetry
        telemetry = {
            "conf_cash": float(self.smoothed_scores[0]),
            "conf_1x": float(self.smoothed_scores[1]),
            "conf_2x": float(self.smoothed_scores[2]),
            "conf_3x": float(self.smoothed_scores[3]),
            "intra_ret": float(intra_ret)
        }

        return self.current_holdings, telemetry

    def update_history(self, price_data):
        """Called by the runner at the end of the day to finalize the candle."""
        self.prices.append(price_data['close'])
        self.highs.append(price_data['high'])
        self.lows.append(price_data['low'])
        self.volumes.append(price_data.get('volume', 0))
        # Update EMA/ATR state here if needed
