import sys
import os
import json
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from etoro_bot.strategy.genome_v9_intra import GenomeV9Intra

def run_backtest():
    print("--- Starting Full Historical Backtest (SPY Inception) ---")
    
    # 1. Load Genome
    genome_path = Path(__file__).parent.parent / "genome.json"
    if not genome_path.exists():
        print(f"Error: genome.json not found at {genome_path}")
        return
        
    with open(genome_path, 'r') as f:
        genome = json.load(f)
    
    strategy = GenomeV9Intra(genome)
    
    # 2. Download Data
    print("Downloading historical data (SPY, VIX, TNX)...")
    spy = yf.download("SPY", start="1993-01-01")
    vix = yf.download("^VIX", start="1993-01-01")
    tnx = yf.download("^TNX", start="1993-01-01")
    irx = yf.download("^IRX", start="1993-01-01")
    
    # Align data
    df = pd.DataFrame(index=spy.index)
    df['Open'] = spy['Open']
    df['High'] = spy['High']
    df['Low'] = spy['Low']
    df['Close'] = spy['Close']
    df['Volume'] = spy['Volume']
    df['vix'] = vix['Close'].reindex(df.index, method='ffill').fillna(15.0)
    
    # Yield Curve Spread (10Y - 3M)
    tnx_data = tnx['Close']
    if isinstance(tnx_data, pd.DataFrame): tnx_data = tnx_data.iloc[:, 0]
    
    irx_data = irx['Close']
    if isinstance(irx_data, pd.DataFrame): irx_data = irx_data.iloc[:, 0]
    
    tnx_c = tnx_data.reindex(df.index, method='ffill').fillna(0.0)
    irx_c = irx_data.reindex(df.index, method='ffill').fillna(0.0)
    df['yield_curve'] = tnx_c - irx_c
    
    # Flatten if multi-indexed
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    print(f"Data loaded: {len(df)} trading days.")
    
    # 3. Simulation
    initial_capital = 10000.0
    equity = initial_capital
    spy_equity = initial_capital # Benchmark
    
    equity_curve = [initial_capital]
    spy_curve = [initial_capital]
    
    returns = []
    spy_returns = []
    
    prev_mid = None
    current_state = "CASH"
    
    for i in range(len(df)):
        current_date = df.index[i]
        row = df.iloc[i]
        
        # Mid-price approximation (17:00 ET is roughly the middle of the daily range or mid of O/C)
        # We'll use (Open + Close) / 2 as a proxy for the 17:00 price
        mid_price = (row['Open'] + row['Close']) / 2.0
        
        # 1. Apply returns from Yesterday's Mid-Price to Today's Mid-Price
        if prev_mid is not None:
            daily_spy_ret = (mid_price - prev_mid) / prev_mid
            spy_equity *= (1 + daily_spy_ret)
            spy_returns.append(daily_spy_ret)
            
            if current_state == "SPY":
                daily_ret = daily_spy_ret
            elif current_state == "2xSPY":
                daily_ret = daily_spy_ret * 2.0
            elif current_state == "3xSPY":
                daily_ret = daily_spy_ret * 3.0
            else: # CASH
                daily_ret = 0.0
                
            equity *= (1 + daily_ret)
            returns.append(daily_ret)
            
        # 2. Strategy runs at Mid-Price
        price_data = {
            'date': current_date.strftime('%Y-%m-%d'),
            'open': float(row['Open']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'close': float(mid_price), # Mid-day price
            'vix': float(row['vix']),
            'yield_curve': float(row['yield_curve'])
        }
        
        holdings, _ = strategy.on_data(current_date, price_data, None)
        current_state = list(holdings.keys())[0]
        
        equity_curve.append(equity)
        spy_curve.append(spy_equity)
        
        # Finalize the day with the TRUE close for the indicators' history
        # (The strategy needs the previous day's REAL close for intra_ret calc)
        strategy.update_history({
            'close': float(row['Close']),
            'high': float(row['High']),
            'low': float(row['Low']),
            'volume': int(row['Volume'])
        })
        
        prev_mid = mid_price
        
    # 4. Results
    def calc_metrics(curve, rets):
        total_ret = (curve[-1] / initial_capital - 1) * 100
        y = len(df) / 252
        cagr_val = ((curve[-1] / initial_capital) ** (1 / y) - 1) * 100
        
        # Drawdown
        peaks = pd.Series(curve).expanding().max()
        drawdowns = (pd.Series(curve) - peaks) / peaks
        max_dd = drawdowns.min() * 100
        
        # Sharpe (Annualized)
        sharpe_val = (np.mean(rets) / np.std(rets)) * np.sqrt(252) if len(rets) > 0 else 0
        
        return total_ret, cagr_val, max_dd, sharpe_val

    years = len(df) / 252
    strat_total, strat_cagr, strat_dd, strat_sharpe = calc_metrics(equity_curve, returns)
    spy_total, spy_cagr, spy_dd, spy_sharpe = calc_metrics(spy_curve, spy_returns)
    
    print("\n" + "="*60)
    print(f"BACKTEST RESULTS ({df.index[0].date()} to {df.index[-1].date()})")
    print("="*60)
    print(f"Metric          | Strategy             | SPY (Buy & Hold)")
    print("-" * 60)
    print(f"Final Equity    | ${equity:,.2f}  | ${spy_equity:,.2f}")
    print(f"Total Return    | {strat_total:,.2f}%      | {spy_total:,.2f}%")
    print(f"CAGR            | {strat_cagr:.2f}%               | {spy_cagr:.2f}%")
    print(f"Max Drawdown    | {strat_dd:.2f}%              | {spy_dd:.2f}%")
    print(f"Sharpe Ratio    | {strat_sharpe:.2f}                 | {spy_sharpe:.2f}")
    print(f"Trading Years   | {years:.2f}                 | {years:.2f}")
    print("="*60)

if __name__ == "__main__":
    run_backtest()
