import sys
import pandas as pd
import yfinance as yf
import numpy as np
from pathlib import Path

# Add project root to path to import etoro_bot
sys.path.append(str(Path(__file__).parent.parent))

from etoro_bot.strategy.eyeball import EyeballStrategy

def run_validation_backtest():
    print("--- Running Strategy Validation Check ---")
    print("This script uses the ACTUAL production EyeballStrategy class.")
    
    # 1. Download Data
    spy = yf.download("SPY", start="2010-01-01")
    vix = yf.download("^VIX", start="2010-01-01")
    gld = yf.download("GLD", start="2010-01-01")
    tlt = yf.download("TLT", start="2010-01-01")
    shy = yf.download("SHY", start="2010-01-01")

    # Helper to get column regardless of MultiIndex
    def get_col(df, price_type):
        if isinstance(df.columns, pd.MultiIndex):
            return df[price_type].iloc[:, 0]
        return df[price_type]

    df = pd.DataFrame({
        'spy_open': get_col(spy, 'Open'),
        'spy_close': get_col(spy, 'Close'),
        'vix': get_col(vix, 'Close'),
        'gld_close': get_col(gld, 'Close'),
        'tlt_close': get_col(tlt, 'Close'),
        'shy_close': get_col(shy, 'Close')
    }).ffill().dropna()

    strategy = EyeballStrategy()
    
    equity = 10000.0
    equity_curve = [equity]
    regimes = []
    last_rebalance_day = 0
    last_regime = None
    
    # Convert df to list of dicts for the strategy class
    history_list = []
    for i in range(len(df)):
        row = df.iloc[i]
        date_str = row.name.strftime('%Y-%m-%d')
        
        # Today's data for the strategy
        todays_data = {
            'date': date_str,
            'open': row['spy_open'],
            'close': row['spy_close'],
            'vix': row['vix']
        }
        
        regime = strategy.get_regime(todays_data, history_list)
        regimes.append(regime)
        
        # Check if rebalance should happen
        regime_changed = (last_regime is not None and regime != last_regime)
        days_since_rebalance = i - last_rebalance_day
        
        should_rebalance = False
        if last_regime is None:
            should_rebalance = True  # Initial
        elif regime_changed:
            should_rebalance = True  # Regime flip always triggers
        elif regime == "BULLISH" and days_since_rebalance >= strategy.REBALANCE_DAYS:
            should_rebalance = True  # 20-day periodic rebalance in bullish only
        
        if should_rebalance:
            last_rebalance_day = i
        
        last_regime = regime
        
        # Calculate daily return based on regime
        if i > 0:
            spy_ret = (row['spy_close'] / df.iloc[i-1]['spy_close']) - 1
            gld_ret = (row['gld_close'] / df.iloc[i-1]['gld_close']) - 1
            tlt_ret = (row['tlt_close'] / df.iloc[i-1]['tlt_close']) - 1
            shy_ret = (row['shy_close'] / df.iloc[i-1]['shy_close']) - 1
            
            if regime == "BULLISH":
                # 6 equal-weight leveraged ETFs
                # SPYU ~ 4x SPY, UPRO ~ 3x SPY, TECL ~ 3x Tech, TNA ~ 3x Russell 2000
                # TQQQ ~ 3x NASDAQ, UDOW ~ 3x Dow
                # Approximate: use SPY as proxy for all (simplistic but reasonable for validation)
                daily_ret = (
                    0.16 * spy_ret * 4.0 +   # SPYU
                    0.16 * spy_ret * 3.0 +   # UPRO
                    0.16 * spy_ret * 3.0 +   # TECL (proxy via SPY)
                    0.16 * spy_ret * 3.0 +   # TNA (proxy via SPY)
                    0.16 * spy_ret * 3.0 +   # TQQQ (proxy via SPY)
                    0.16 * spy_ret * 3.0      # UDOW (proxy via SPY)
                )
            else:
                # PANIC: GOLD: 60%, TLT: 25%, SHY: 10%, 4xSPY: 5%
                daily_ret = (0.60 * gld_ret) + (0.25 * tlt_ret) + (0.10 * shy_ret) + (0.05 * spy_ret * 4.0)
            
            equity *= (1 + daily_ret)
            equity_curve.append(equity)

        # Update history for next iteration
        history_list.append({
            'open': row['spy_open'],
            'close': row['spy_close']
        })

    # Results
    final_return = (equity / 10000.0 - 1) * 100
    panic_days = regimes.count("PANIC")
    bullish_days = regimes.count("BULLISH")
    
    print(f"\nValidation Period: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Initial Equity: $10,000.00")
    print(f"Final Equity:   ${equity:,.2f}")
    print(f"Total Return:   {final_return:.2f}%")
    print(f"Panic Days:     {panic_days} / {len(regimes)}")
    print(f"Bullish Days:   {bullish_days} / {len(regimes)}")
    
    # Check for regime switches
    switches = 0
    for i in range(1, len(regimes)):
        if regimes[i] != regimes[i-1]:
            switches += 1
    print(f"Regime Switches: {switches}")

if __name__ == "__main__":
    run_validation_backtest()
