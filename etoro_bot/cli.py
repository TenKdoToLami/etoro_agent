import argparse
import sys
import warnings
from pprint import pprint

# Suppress annoying third-party warnings
warnings.simplefilter("ignore")
try:
    import pandas as pd
    pd.options.mode.chained_assignment = None
except ImportError:
    pass

from .core.etoro import EtoroAPI
from .data.market import DataManager
from .config import ETORO_USER_KEY, ETORO_API_KEY
from .daily_job import main as run_daily_job

def get_api():
    return EtoroAPI(api_key=ETORO_API_KEY, user_key=ETORO_USER_KEY)

def main():
    parser = argparse.ArgumentParser(description="eToro Agent Portfolio CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("status", help="Check if market is open according to yfinance")
    
    subparsers.add_parser("portfolio", help="Show current equity, cash, and invested amounts")
    
    subparsers.add_parser("positions", help="List all open positions")
    
    buy_parser = subparsers.add_parser("buy", help="Open a new position")
    buy_parser.add_argument("--symbol", type=str, required=True, help="Symbol to buy (e.g. SPY)")
    buy_parser.add_argument("--amount", type=float, required=True, help="Amount in USD to invest")
    
    sell_parser = subparsers.add_parser("sell", help="Close a position")
    sell_parser.add_argument("--id", type=str, required=True, help="Position ID to close")
    
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a pending order")
    cancel_parser.add_argument("--id", type=str, required=True, help="Order ID to cancel")
    
    resolve_parser = subparsers.add_parser("resolve", help="Get Instrument ID from symbol")
    resolve_parser.add_argument("--symbol", type=str, required=True, help="Symbol to resolve (e.g. AAPL)")
    
    price_parser = subparsers.add_parser("price", help="Get current market price for a symbol")
    price_parser.add_argument("--symbol", type=str, required=True, help="Symbol to check (e.g. WISE.L)")
    
    run_job_parser = subparsers.add_parser("run-job", help="Execute the daily trading job manually")
    run_job_parser.add_argument("--force", action="store_true", help="Force run even if market is closed")
    run_job_parser.add_argument("--dry-run", action="store_true", help="Log intended trades without executing them")
    
    args = parser.parse_args()
    
    if args.command == "status":
        dm = DataManager()
        is_open = dm.is_market_open_today()
        print(f"Market Status: {'OPEN / DATA AVAILABLE' if is_open else 'CLOSED / NO DATA'}")
        
    elif args.command == "portfolio":
        api = get_api()
        pnl = api.get_pnl()
        client_portfolio = pnl.get("clientPortfolio", {})
        credit = client_portfolio.get("credit", 0.0)
        positions = client_portfolio.get("positions", [])
        orders_for_open = client_portfolio.get("ordersForOpen", [])
        
        # Calculate manual (non-mirror) pending orders
        pending_amount = sum(o.get("amount", 0.0) for o in orders_for_open if o.get("mirrorID", 0) == 0)
        
        total_invested = sum(p.get("amount", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
        unrealized_pnl = sum(p.get("unrealizedPnL", {}).get("pnL", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
        
        print(f"Equity:   ${credit + total_invested + unrealized_pnl:.2f}")
        print(f"Cash:     ${credit - pending_amount:.2f} (Available)")
        print(f"Pending:  ${pending_amount:.2f}")
        print(f"Invested: ${total_invested:.2f}")
        
    elif args.command == "positions":
        api = get_api()
        pnl = api.get_pnl()
        client_portfolio = pnl.get("clientPortfolio", {})
        positions = client_portfolio.get("positions", [])
        orders_for_open = client_portfolio.get("ordersForOpen", [])
        
        manual_positions = [p for p in positions if p.get("mirrorID", 0) == 0]
        manual_orders = [o for o in orders_for_open if o.get("mirrorID", 0) == 0]
        
        if not manual_positions and not manual_orders:
            print("No open positions or pending orders.")
        else:
            if manual_positions:
                print("--- Open Positions ---")
                for p in manual_positions:
                    print(f"ID: {p.get('positionID')} | InstrumentID: {p.get('instrumentID')} | Amount: ${p.get('amount')} | PnL: ${p.get('unrealizedPnL', {}).get('pnL', 0)}")
            
            if manual_orders:
                if manual_positions: print("")
                print("--- Pending Orders ---")
                for o in manual_orders:
                    print(f"OrderID: {o.get('orderID')} | InstrumentID: {o.get('instrumentID')} | Amount: ${o.get('amount')} | Status: {o.get('statusID')}")
                
    elif args.command == "buy":
        api = get_api()
        try:
            instrument_id = api.resolve_instrument(args.symbol)
            print(f"Resolved {args.symbol} to Instrument ID {instrument_id}. Opening position...")
            res = api.open_position(instrument_id, args.amount)
            print("Success:")
            pprint(res)
        except Exception as e:
            print(f"Failed to open position: {e}")
            
    elif args.command == "sell":
        api = get_api()
        try:
            pnl = api.get_pnl()
            positions = pnl.get("clientPortfolio", {}).get("positions", [])
            pos = next((p for p in positions if str(p.get("positionID")) == args.id), None)
            
            if not pos:
                print(f"Error: Position ID {args.id} not found in portfolio.")
            else:
                iid = pos.get("instrumentID")
                print(f"Closing position ID {args.id} (InstrumentID {iid})...")
                res = api.close_position(args.id, iid)
                print("Success:")
                pprint(res)
        except Exception as e:
            print(f"Failed to close position: {e}")
            
    elif args.command == "cancel":
        api = get_api()
        try:
            print(f"Cancelling order ID {args.id}...")
            res = api.cancel_order(args.id)
            print("Success:")
            pprint(res)
        except Exception as e:
            print(f"Failed to cancel order: {e}")
            
    elif args.command == "resolve":
        api = get_api()
        try:
            iid = api.resolve_instrument(args.symbol)
            print(f"Symbol: {args.symbol} | InstrumentID: {iid}")
        except Exception as e:
            print(f"Error: {e}")
            
    elif args.command == "price":
        try:
            import yfinance as yf
            ticker = yf.Ticker(args.symbol)
            # Use fast_info or history to get the latest price
            price = ticker.fast_info['last_price']
            currency = ticker.fast_info['currency']
            print(f"Symbol: {args.symbol} | Current Price: {price:.2f} {currency}")
        except Exception as e:
            print(f"Error fetching price for {args.symbol}: {e}")
            
    elif args.command == "run-job":
        run_daily_job(force=args.force, dry_run=args.dry_run)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
