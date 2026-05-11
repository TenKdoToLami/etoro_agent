from datetime import datetime, timedelta
import time
from ..strategy.eyeball import EyeballStrategy
from ..config import STATE_TO_SYMBOL, SAFETY_CASH, MIN_POSITION_VALUE
from .etoro import EtoroAPI
from ..data.portfolio import SnapshotManager
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class TradingLogic:
    def __init__(self, etoro_api: EtoroAPI):
        self.etoro = etoro_api
        self.snapshot_manager = SnapshotManager()

    def get_portfolio_weights(self):
        """Calculates current weights of assets in the portfolio."""
        pnl = self.etoro.get_pnl()
        client_portfolio = pnl.get("clientPortfolio", {})
        
        credit = client_portfolio.get("credit", 0.0)
        positions = client_portfolio.get("positions", [])
        
        # We only care about manual positions
        manual_positions = [p for p in positions if p.get("mirrorID", 0) == 0]
        
        total_invested = sum(p.get("amount", 0.0) for p in manual_positions)
        unrealized_pnl = sum(p.get("unrealizedPnL", {}).get("pnL", 0.0) for p in manual_positions)
        equity = credit + total_invested + unrealized_pnl
        
        if equity <= 0:
            return {}, 0
            
        weights = {}
        # Reverse map symbols back to our keys (e.g., UPRO -> UPRO)
        SYMBOL_TO_STATE = {v: k for k, v in STATE_TO_SYMBOL.items()}
        
        for pos in manual_positions:
            symbol = pos.get("displaySymbol") # eToro API often includes this
            state_key = SYMBOL_TO_STATE.get(symbol, "OTHER")
            
            pos_value = pos.get("amount", 0.0) + pos.get("unrealizedPnL", {}).get("pnL", 0.0)
            weights[state_key] = weights.get(state_key, 0.0) + (pos_value / equity)
            
        weights["CASH"] = credit / equity
        return weights, equity

    def get_target_decision(self, historical_data, todays_data):
        """
        Evaluates the Eyeball strategy and decides if a rebalance is needed.
        
        Rebalance logic:
          - Regime change (PANIC <-> BULLISH) → always rebalance
          - In BULLISH mode → rebalance every N trading days (default 20)
          - In PANIC mode → only rebalance on regime change (no periodic)
        
        Returns (target_weights, regime, should_rebalance, reason)
        """
        strategy = EyeballStrategy()
        target_weights, telemetry = strategy.on_data(todays_data, historical_data)
        regime = telemetry['regime']
        
        # 1. Check for regime change → always rebalance
        last_date, last_weights, last_regime = self.snapshot_manager.get_last_rebalance()
        
        if last_regime is None:
            return target_weights, regime, True, "Initial rebalance (no prior state)"
        
        if regime != last_regime:
            return target_weights, regime, True, f"Regime change: {last_regime} -> {regime}"
        
        # 2. In PANIC mode, do NOT periodic-rebalance — only regime flip triggers trades
        if regime == "PANIC":
            return target_weights, regime, False, "PANIC mode — holding until regime flips to BULLISH"
        
        # 3. In BULLISH mode, rebalance every REBALANCE_DAYS trading days
        if last_date:
            last_dt = datetime.strptime(last_date, '%Y-%m-%d')
            today_dt = datetime.strptime(todays_data['date'], '%Y-%m-%d')
            days_since = (today_dt - last_dt).days
            
            if days_since >= strategy.REBALANCE_DAYS:
                return target_weights, regime, True, f"Periodic {strategy.REBALANCE_DAYS}-day rebalance ({days_since} days since last trade)"
            else:
                return target_weights, regime, False, f"Next rebalance in {strategy.REBALANCE_DAYS - days_since} days ({days_since}/{strategy.REBALANCE_DAYS})"

        return target_weights, regime, False, "No rebalance needed"

    def execute_rebalance(self, target_weights, regime, todays_data, dry_run=False):
        """
        Executes trades to reach target weights.
        """
        logger.info(f"Executing rebalance to target weights: {target_weights} (Regime: {regime})")
        
        current_weights, equity = self.get_portfolio_weights()
        investable_equity = equity - SAFETY_CASH
        
        if investable_equity <= 0:
            logger.warning("Insufficient equity to rebalance.")
            return

        # Simple execution strategy for eToro:
        # 1. Close all positions that are NOT in target or need substantial reduction
        # 2. Open new positions to match target amounts
        
        pnl = self.etoro.get_pnl()
        positions = pnl.get("clientPortfolio", {}).get("positions", [])
        manual_positions = [p for p in positions if p.get("mirrorID", 0) == 0]
        
        # Group positions by symbol
        for pos in manual_positions:
            symbol = pos.get("displaySymbol")
            pid = pos.get("positionID")
            iid = pos.get("instrumentID")
            
            # If symbol not in target weights, close it
            SYMBOL_TO_STATE = {v: k for k, v in STATE_TO_SYMBOL.items()}
            state_key = SYMBOL_TO_STATE.get(symbol)
            
            if state_key not in target_weights:
                logger.info(f"Closing position {pid} for {symbol} (not in target)")
                if not dry_run:
                    self.etoro.close_position(pid, iid)
                    time.sleep(2)
            else:
                # Close and reopen to reset exact weights
                logger.info(f"Closing position {pid} for {symbol} to reset weight")
                if not dry_run:
                    self.etoro.close_position(pid, iid)
                    time.sleep(2)

        if not dry_run:
            logger.info("Waiting for eToro PnL cache to refresh...")
            time.sleep(60)
            # Refresh equity after closes
            pnl = self.etoro.get_pnl()
            available_cash = pnl.get("clientPortfolio", {}).get("credit", 0.0)
            investable_cash = available_cash - SAFETY_CASH
        else:
            investable_cash = investable_equity # Mock

        # Open new positions
        for state_key, weight in target_weights.items():
            amount = investable_cash * (weight / sum(target_weights.values())) # Normalize weights
            symbol = STATE_TO_SYMBOL.get(state_key)
            if not symbol:
                logger.error(f"No symbol found for state: {state_key}")
                continue
                
            if amount > MIN_POSITION_VALUE:
                logger.info(f"Opening position: {symbol} | Amount: ${amount:.2f}")
                if not dry_run:
                    try:
                        iid = self.etoro.resolve_instrument(symbol)
                        self.etoro.open_position(iid, amount)
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"Failed to open position for {symbol}: {e}")
            else:
                logger.info(f"Amount ${amount:.2f} for {symbol} is below MIN_POSITION_VALUE. Skipping.")

        # Log the rebalance
        if not dry_run:
            self.snapshot_manager.log_rebalance(todays_data['date'], target_weights, regime)
