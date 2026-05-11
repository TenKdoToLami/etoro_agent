import numpy as np
import pandas as pd
from .indicators import sma, ema
from ..config import VIX_THRESHOLD, REBALANCE_INTERVAL_DAYS

class EyeballStrategy:
    NAME = "EYEBALL (SmoothDriftStrategy V3)"
    
    # Target Weights — Bullish: equal-weight leveraged ETFs
    BULLISH_WEIGHTS = {
        "SPYU": 0.16,
        "UPRO": 0.16,
        "TECL": 0.16,
        "TNA": 0.16,
        "TQQQ": 0.16,
        "UDOW": 0.16,
    }
    
    # Panic: safe-haven allocation
    PANIC_WEIGHTS = {
        "GOLD": 0.60,
        "TLT": 0.25,
        "SHY": 0.10,
        "4xSPY": 0.05,
    }
    
    VIX_THRESHOLD = VIX_THRESHOLD           # default 32
    REBALANCE_DAYS = REBALANCE_INTERVAL_DAYS  # default 20
    
    def __init__(self):
        self.reset()

    def reset(self):
        self.prices = []
    
    def get_regime(self, todays_data, historical_data):
        """
        Determines the current regime (BULLISH or PANIC) based on VIX and Death Cross.
        
        Panic triggers:
          - VIX >= VIX_THRESHOLD (default 32)
          - Death Cross: SMA 50 < EMA 200 on SPY daily opens
        """
        vix = todays_data.get('vix', 0.0)
        
        # Collect SPY opens for moving-average cross
        opens = [d['open'] for d in historical_data] + [todays_data['open']]
        
        if len(opens) < 200:
            # Not enough data for EMA 200, fall back to VIX-only
            return "PANIC" if vix >= self.VIX_THRESHOLD else "BULLISH"
            
        # SMA 50
        sma_50 = np.mean(opens[-50:])
        # EMA 200
        ema_200 = pd.Series(opens).ewm(span=200, adjust=False).mean().iloc[-1]
        
        death_cross = sma_50 < ema_200
        vix_panic = vix >= self.VIX_THRESHOLD
        
        if vix_panic or death_cross:
            return "PANIC"
        return "BULLISH"

    def get_target_weights(self, regime):
        if regime == "PANIC":
            return self.PANIC_WEIGHTS
        return self.BULLISH_WEIGHTS

    def on_data(self, todays_data, historical_data):
        """
        Returns target weights and telemetry.
        """
        regime = self.get_regime(todays_data, historical_data)
        target_weights = self.get_target_weights(regime)
        
        telemetry = {
            "regime": regime,
            "vix": todays_data.get('vix'),
            "target_weights": target_weights,
        }
        
        return target_weights, telemetry
