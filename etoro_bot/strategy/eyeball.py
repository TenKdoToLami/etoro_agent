import numpy as np
import pandas as pd
from .indicators import sma, ema

class EyeballStrategy:
    NAME = "EYEBALL (SmoothDriftStrategy V2)"
    
    # Target Weights
    NORMAL_WEIGHTS = {
        "4xSPY": 0.65,
        "3xSPY": 0.35
    }
    
    PANIC_WEIGHTS = {
        "GOLD": 0.60,
        "TLT": 0.25,
        "SHY": 0.10,
        "4xSPY": 0.05
    }
    
    VIX_THRESHOLD = 43.0
    TOLERANCE_BAND = 0.10  # 10.0%
    
    def __init__(self):
        self.reset()

    def reset(self):
        self.prices = []
    
    def get_regime(self, todays_data, historical_data):
        """
        Determines the current regime (NORMAL or PANIC) based on VIX and Death Cross.
        """
        vix = todays_data.get('vix', 0.0)
        
        # Collect prices for SMA/EMA
        # historical_data is a list of dicts with 'close'
        prices = [d['close'] for d in historical_data]
        # SMA 50 < EMA 200 calculated on SPY daily open
        # Wait, the spec says "calculated on SPY daily open"
        opens = [d['open'] for d in historical_data] + [todays_data['open']]
        
        if len(opens) < 200:
            # Not enough data for EMA 200, default to NORMAL if VIX is low
            return "PANIC" if vix >= self.VIX_THRESHOLD else "NORMAL"
            
        # SMA 50
        sma_50 = np.mean(opens[-50:])
        # EMA 200
        # Simple EMA implementation or use indicators.py if available
        # indicators.py has ema(prices, period, prev_ema)
        # Let's calculate it properly using pandas for reliability if needed, 
        # but indicators.py is already there.
        
        ema_200 = pd.Series(opens).ewm(span=200, adjust=False).mean().iloc[-1]
        
        death_cross = sma_50 < ema_200
        vix_panic = vix >= self.VIX_THRESHOLD
        
        if vix_panic or death_cross:
            return "PANIC"
        return "NORMAL"

    def get_target_weights(self, regime):
        if regime == "PANIC":
            return self.PANIC_WEIGHTS
        return self.NORMAL_WEIGHTS

    def on_data(self, todays_data, historical_data):
        """
        Returns target weights and telemetry.
        """
        regime = self.get_regime(todays_data, historical_data)
        target_weights = self.get_target_weights(regime)
        
        telemetry = {
            "regime": regime,
            "vix": todays_data.get('vix'),
            "target_weights": target_weights
        }
        
        return target_weights, telemetry
