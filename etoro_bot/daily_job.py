import sys
from pathlib import Path
import time

from .core.etoro import EtoroAPI
from .data.market import DataManager
from .core.engine import TradingLogic
from .data.portfolio import SnapshotManager
from .config import ETORO_USER_KEY, ETORO_API_KEY
from .utils.logger import setup_logger

logger = setup_logger("daily_job")

def log_portfolio_state(etoro_api, prefix=""):
    try:
        pnl = etoro_api.get_pnl()
        client_portfolio = pnl.get("clientPortfolio", {})
        
        credit = client_portfolio.get("credit", 0.0)
        positions = client_portfolio.get("positions", [])
        
        # simplified total invested
        total_invested = sum(p.get("amount", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
        unrealized_pnl = sum(p.get("unrealizedPnL", {}).get("pnL", 0.0) for p in positions if p.get("mirrorID", 0) == 0)
        equity = credit + total_invested + unrealized_pnl
        
        logger.info(f"{prefix} Equity: ${equity:.2f} | Cash: ${credit:.2f} | Invested: ${total_invested:.2f} | Open Positions: {len(positions)}")
    except Exception as e:
        logger.error(f"Failed to log portfolio state: {e}")

def main(force=False, dry_run=False):
    logger.info("--- Starting Daily eToro Job ---")
    
    if not ETORO_USER_KEY or ETORO_USER_KEY == "your_agent_portfolio_user_token_here":
        logger.error("ETORO_USER_KEY is not set. Please configure .env file.")
        return

    data_manager = DataManager()
    
    if not data_manager.is_market_open_today() and not force:
        logger.info("Market is not open or data not available for today. Exiting.")
        return
        
    try:
        # 1. Update data
        logger.info("Updating historical data...")
        data_manager.update_historical_data()
        
        history = data_manager.get_historical_data()
        todays_data = data_manager.get_todays_price()
        
        if not todays_data:
            if force and history:
                logger.info("Using last historical candle as mock for today's price (FORCE mode).")
                todays_data = history[-1]
            else:
                logger.error("Failed to fetch today's data. Exiting.")
                return
            
        logger.info(f"Loaded {len(history)} days of history. Today's SPY mid-price: {todays_data['close']}")
        
        # 2. Init API and Logic
        etoro_api = EtoroAPI(api_key=ETORO_API_KEY, user_key=ETORO_USER_KEY)
        trading_logic = TradingLogic(etoro_api)
        
        # 3. Log initial state
        log_portfolio_state(etoro_api, prefix="[BEFORE]")
        
        # 4. Target Decision
        target_weights, regime, should_rebalance, reason = trading_logic.get_target_decision(history, todays_data)
        logger.info(f"Strategy Decision: should_rebalance={should_rebalance} | Reason: {reason}")
        logger.info(f"Target Weights: {target_weights} (Regime: {regime})")
        
        # 5. Execute
        if should_rebalance or force:
            if force: logger.info("FORCE mode enabled - executing rebalance regardless of strategy decision.")
            trading_logic.execute_rebalance(target_weights, regime, todays_data, dry_run=dry_run)
        else:
            logger.info("No rebalance required today.")
        
        # Wait a bit before final log
        time.sleep(5)
        
        # 6. Log final state
        log_portfolio_state(etoro_api, prefix="[AFTER]")
        
        # 7. Take snapshot
        logger.info("Taking daily snapshot of portfolio...")
        snapshot_manager = SnapshotManager()
        snapshot_manager.take_snapshot(etoro_api)
        
        logger.info("--- Daily Job Completed Successfully ---")
        
    except Exception as e:
        logger.exception(f"An error occurred during the daily job: {e}")

if __name__ == "__main__":
    main()
