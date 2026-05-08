import sys
import pandas as pd
import yfinance as yf
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def run_backtest():
    print("--- Starting OPTIMIZED EYEBALL Strategy Backtest ---")
    
    # 1. Download Data
    print("Downloading historical data (SPY, VIX, GLD, TLT, SHY)...")
    start_date = "2005-01-01"
    assets = ["SPY", "^VIX", "GLD", "TLT", "SHY"]
    data = yf.download(assets, start=start_date)['Close']
    
    # Standardize names
    df = data.rename(columns={"^VIX": "vix", "SPY": "spy_price", "GLD": "gld_price", "TLT": "tlt_price", "SHY": "shy_price"})
    df = df.ffill().dropna()
    
    # 2. Pre-calculate Indicators (Vectorized)
    print("Calculating indicators...")
    df['sma50'] = df['spy_price'].rolling(window=50).mean()
    df['ema200'] = df['spy_price'].ewm(span=200, adjust=False).mean()
    
    # 3. Determine Regime (Vectorized)
    df['death_cross'] = df['sma50'] < df['ema200']
    df['vix_panic'] = df['vix'] >= 43.0
    df['is_panic'] = df['vix_panic'] | df['death_cross']
    
    # 4. Simulation Setup
    initial_capital = 10000.0
    equity = initial_capital
    spy_equity = initial_capital
    
    equity_curve = [initial_capital]
    spy_curve = [initial_capital]
    
    # Expenses (Annual)
    DRAG_3X = 0.0095 
    DRAG_4X = 0.0125 
    DRAG_ETF = 0.0020
    
    # Returns (Daily)
    df['spy_ret'] = df['spy_price'].pct_change()
    df['gld_ret'] = df['gld_price'].pct_change()
    df['tlt_ret'] = df['tlt_price'].pct_change()
    df['shy_ret'] = df['shy_price'].pct_change()
    
    print(f"Simulating {len(df)} days...")
    
    # We iterate once, but no O(N^2) work inside
    rets = []
    spy_rets = []
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        is_panic = row['is_panic']
        
        spy_ret = row['spy_ret']
        
        if not is_panic:
            # NORMAL Mode
            # 4x SPY: 65%, 3x SPY: 35%
            daily_ret = (0.65 * (spy_ret * 4.0 - DRAG_4X/252)) + \
                        (0.35 * (spy_ret * 3.0 - DRAG_3X/252))
        else:
            # PANIC Mode
            # GOLD: 60%, TLT: 25%, SHY: 10%, 4x SPY: 5%
            daily_ret = (0.60 * (row['gld_ret'] - DRAG_ETF/252)) + \
                        (0.25 * (row['tlt_ret'] - DRAG_ETF/252)) + \
                        (0.10 * (row['shy_ret'] - DRAG_ETF/252)) + \
                        (0.05 * (spy_ret * 4.0 - DRAG_4X/252))
            
        equity *= (1 + daily_ret)
        spy_equity *= (1 + spy_ret)
        
        equity_curve.append(equity)
        spy_curve.append(spy_equity)
        rets.append(daily_ret)
        spy_rets.append(spy_ret)

    # 5. Results
    def get_metrics(curve, r):
        total_ret = (curve[-1] / initial_capital - 1) * 100
        years = len(r) / 252
        cagr = ((curve[-1] / initial_capital) ** (1/years) - 1) * 100
        peaks = pd.Series(curve).expanding().max()
        max_dd = ((pd.Series(curve) - peaks) / peaks).min() * 100
        sharpe = (np.mean(r) / np.std(r)) * np.sqrt(252)
        return total_ret, cagr, max_dd, sharpe

    strat_m = get_metrics(equity_curve, rets)
    spy_m = get_metrics(spy_curve, spy_rets)
    
    print("\n" + "="*60)
    print(f"EYEBALL BACKTEST RESULTS (2005 - Present)")
    print("="*60)
    print(f"{'Metric':<15} | {'EYEBALL (4x/3x)':<20} | {'SPY (1x)':<20}")
    print("-" * 60)
    print(f"{'Total Return':<15} | {strat_m[0]:>18.2f}% | {spy_m[0]:>18.2f}%")
    print(f"{'CAGR':<15} | {strat_m[1]:>18.2f}% | {spy_m[1]:>18.2f}%")
    print(f"{'Max Drawdown':<15} | {strat_m[2]:>18.2f}% | {spy_m[2]:>18.2f}%")
    print(f"{'Sharpe Ratio':<15} | {strat_m[3]:>18.2f}  | {spy_m[3]:>18.2f}")
    print("="*60)

if __name__ == "__main__":
    run_backtest()
