"""
Core trading logic: evaluates the V9 Intra strategy against market data
and translates state transitions into eToro trades.
"""

import json
import time
from pathlib import Path

from ..strategy import GenomeV9Intra
from ..config import STATE_TO_SYMBOL, SAFETY_CASH, MIN_POSITION_VALUE, GENOME_PATH
from .etoro import EtoroAPI
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TradingLogic:
    def __init__(self, etoro_api: EtoroAPI):
        self.etoro = etoro_api
        self.genome_path = Path(GENOME_PATH)

    # ------------------------------------------------------------------
    # Strategy evaluation
    # ------------------------------------------------------------------
    def get_target_state(self, historical_data, todays_data):
        """Feed all historical candles + today's intraday candle through the
        neural-net strategy and return the symbolic target state
        (e.g. ``"CASH"``, ``"SPY"``, ``"2xSPY"``, ``"3xSPY"``)."""

        with open(self.genome_path, 'r') as f:
            genome = json.load(f)

        strategy = GenomeV9Intra(genome)

        # Replay history to warm up indicators
        prev_data = None
        for day_data in historical_data:
            strategy.on_data(day_data['date'], day_data, prev_data)
            strategy.update_history(day_data)
            prev_data = day_data

        # Evaluate today
        target_holdings, telemetry = strategy.on_data(
            todays_data['date'], todays_data, prev_data
        )

        # holdings is e.g. {"SPY": 1.0} or {"CASH": 1.0}
        target_state = list(target_holdings.keys())[0]
        logger.info(f"Target state: {target_state}  |  Telemetry: {telemetry}")
        return target_state

    # ------------------------------------------------------------------
    # Trade execution
    # ------------------------------------------------------------------
    def execute_trades(self, target_state):
        """Compare the current eToro portfolio against *target_state* and
        execute the minimum set of trades to converge."""

        pnl = self.etoro.get_pnl()
        client_portfolio = pnl.get("clientPortfolio", {})

        available_cash = client_portfolio.get("credit", 0.0)
        positions = client_portfolio.get("positions", [])
        orders_for_open = client_portfolio.get("ordersForOpen", [])

        # Deduct pending manual orders from available cash
        for order in orders_for_open:
            if order.get("mirrorID") == 0:
                available_cash -= order.get("amount", 0.0)

        # Collect manual (non-mirror) positions only
        manual_positions = [p for p in positions if p.get("mirrorID", 0) == 0]

        # Resolve target symbol — every state maps to a tradeable symbol
        # (CASH maps to the bonds ETF configured in .env)
        target_symbol = STATE_TO_SYMBOL.get(target_state, "BND")
        target_instrument_id = self.etoro.resolve_instrument(target_symbol)

        logger.info(
            f"Manual positions: {len(manual_positions)} | "
            f"Target: {target_symbol} (instrumentID={target_instrument_id})"
        )

        # ---- Close positions that don't match the target ----
        positions_to_close = []
        for pos in manual_positions:
            if pos.get("instrumentID") != target_instrument_id:
                positions_to_close.append(pos.get("positionID"))

        if positions_to_close:
            logger.info(
                f"State changed — closing {len(positions_to_close)} position(s)."
            )
            for pid in positions_to_close:
                logger.info(f"  Closing positionID {pid}")
                self.etoro.close_position(pid)
                time.sleep(4)  # rate-limit spacing

            logger.info(
                "Waiting 60 s for eToro PnL cache to refresh after closes…"
            )
            time.sleep(60)

            # Refresh cash balance
            pnl = self.etoro.get_pnl()
            available_cash = pnl.get("clientPortfolio", {}).get("credit", 0.0)

        # ---- Open new position with surplus cash ----
        investable_cash = available_cash - SAFETY_CASH

        if investable_cash > MIN_POSITION_VALUE:
            logger.info(
                f"Opening position: {target_symbol}  |  amount=${investable_cash:.2f}"
            )
            self.etoro.open_position(
                instrument_id=target_instrument_id,
                amount=investable_cash,
                is_buy=True,
                leverage=1,
            )
        else:
            logger.info(
                f"Investable cash ${investable_cash:.2f} is below "
                f"MIN_POSITION_VALUE ${MIN_POSITION_VALUE}. Holding."
            )
