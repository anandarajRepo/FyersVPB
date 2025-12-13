# strategy/volume_profile_strategy.py

"""
Volume Profile Breakout Strategy Implementation
Trades breakouts of Value Area High (VAH) and Value Area Low (VAL)
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from config.settings import FyersConfig, VolumeProfileStrategyConfig, TradingConfig, SignalType, VolumeProfilePeriod
from config.symbols import symbol_manager, get_vp_symbols, validate_vp_symbol
from models.trading_models import (
    Position, VolumeProfileSignal, VolumeProfileData, LiveQuote, TradeResult,
    StrategyMetrics, MarketState, create_vp_signal_from_symbol,
    create_position_from_signal, create_trade_result_from_position
)
from services.volume_profile_service import VolumeProfileCalculator

logger = logging.getLogger(__name__)


class VolumeProfileBreakoutStrategy:
    """Volume Profile Breakout Trading Strategy"""

    def __init__(
            self,
            fyers_config: FyersConfig,
            strategy_config: VolumeProfileStrategyConfig,
            trading_config: TradingConfig
    ):
        # Configuration
        self.fyers_config = fyers_config
        self.strategy_config = strategy_config
        self.trading_config = trading_config

        # Volume Profile Calculator
        self.vp_calculator = VolumeProfileCalculator(
            price_buckets=strategy_config.price_buckets,
            value_area_pct=strategy_config.value_area_pct
        )

        # Strategy state
        self.positions: Dict[str, Position] = {}
        self.completed_trades: List[TradeResult] = []
        self.metrics = StrategyMetrics()
        self.market_state = MarketState(timestamp=datetime.now())

        # Volume Profile state
        self.volume_profiles: Dict[str, VolumeProfileData] = {}
        self.vp_calculated = False
        self.signals_generated_today = []

        # Performance tracking
        self.daily_pnl = 0.0
        self.max_daily_loss = self.strategy_config.portfolio_value * 0.02

        # Get trading universe
        self.trading_symbols = get_vp_symbols()
        logger.info(f"VP Strategy initialized with {len(self.trading_symbols)} symbols")

        # Real-time data tracking
        self.live_quotes: Dict[str, LiveQuote] = {}

        # Breakout tracking
        self.breakout_detected: Dict[str, str] = {}  # symbol -> "VAH" or "VAL"

    async def initialize(self) -> bool:
        """Initialize strategy and services"""
        try:
            logger.info("Initializing Volume Profile Breakout Strategy...")

            # Initialize market state
            self._update_market_state()

            logger.info(f"Strategy initialized successfully:")
            logger.info(f"  Total symbols: {len(self.trading_symbols)}")
            logger.info(f"  Max positions: {self.strategy_config.max_positions}")
            logger.info(f"  Risk per trade: {self.strategy_config.risk_per_trade_pct}%")
            logger.info(f"  VP Period: {self.strategy_config.vp_period.value}")

            return True

        except Exception as e:
            logger.error(f"Strategy initialization failed: {e}")
            return False

    def _on_live_data_update(self, symbol: str, live_quote: LiveQuote):
        """Handle real-time data updates"""
        try:
            # Validate symbol
            if not validate_vp_symbol(symbol):
                return

            # Update internal storage
            self.live_quotes[symbol] = live_quote

            # Add tick data to VP calculator
            self.vp_calculator.add_tick_data(
                symbol,
                live_quote.ltp,
                live_quote.volume,
                live_quote.timestamp
            )

            # Update position tracking if we have a position
            if symbol in self.positions:
                self._update_position_tracking(symbol, live_quote)

            # Check for breakouts (only if VP is calculated)
            if self.vp_calculated and symbol in self.volume_profiles:
                self._check_for_breakout(symbol, live_quote)

        except Exception as e:
            logger.error(f"Error handling live data for {symbol}: {e}")

    def _update_position_tracking(self, symbol: str, live_quote: LiveQuote):
        """Update position tracking with current price"""
        try:
            position = self.positions[symbol]
            current_price = live_quote.ltp

            # Update price extremes
            position.update_price_extremes(current_price)

            # Calculate unrealized P&L
            if position.signal_type == SignalType.LONG:
                position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
            else:
                position.unrealized_pnl = (position.entry_price - current_price) * abs(position.quantity)

            # Update trailing stop if enabled
            if self.strategy_config.enable_trailing_stops:
                self._update_trailing_stop(position, current_price)

        except Exception as e:
            logger.error(f"Error updating position tracking for {symbol}: {e}")

    def _update_trailing_stop(self, position: Position, current_price: float):
        """Update trailing stop loss"""
        try:
            if position.signal_type == SignalType.LONG:
                # Trail stop below highest price
                new_stop = position.highest_price * (1 - self.strategy_config.trailing_stop_pct / 100)
                if new_stop > position.current_stop_loss:
                    position.current_stop_loss = new_stop
                    logger.info(f"Trailing stop updated for {position.symbol}: Rs.{new_stop:.2f}")
            else:
                # Trail stop above lowest price
                new_stop = position.lowest_price * (1 + self.strategy_config.trailing_stop_pct / 100)
                if new_stop < position.current_stop_loss:
                    position.current_stop_loss = new_stop
                    logger.info(f"Trailing stop updated for {position.symbol}: Rs.{new_stop:.2f}")

        except Exception as e:
            logger.error(f"Error updating trailing stop for {position.symbol}: {e}")

    def _check_for_breakout(self, symbol: str, live_quote: LiveQuote):
        """Check if price has broken out of value area"""
        try:
            # Skip if already detected breakout for this symbol today
            if symbol in self.breakout_detected:
                return

            vp_data = self.volume_profiles[symbol]
            current_price = live_quote.ltp

            # Check for VAH breakout (upside)
            if current_price > vp_data.vah:
                distance_pct = (current_price - vp_data.vah) / vp_data.vah * 100

                if distance_pct >= self.strategy_config.min_breakout_distance_pct:
                    logger.info(f"VAH Breakout detected: {symbol} at Rs.{current_price:.2f} "
                                f"(VAH: Rs.{vp_data.vah:.2f}, Distance: {distance_pct:.2f}%)")
                    self.breakout_detected[symbol] = "VAH"

            # Check for VAL breakout (downside)
            elif current_price < vp_data.val:
                distance_pct = (vp_data.val - current_price) / vp_data.val * 100

                if distance_pct >= self.strategy_config.min_breakout_distance_pct:
                    logger.info(f"VAL Breakout detected: {symbol} at Rs.{current_price:.2f} "
                                f"(VAL: Rs.{vp_data.val:.2f}, Distance: {distance_pct:.2f}%)")
                    self.breakout_detected[symbol] = "VAL"

        except Exception as e:
            logger.error(f"Error checking breakout for {symbol}: {e}")

    async def calculate_volume_profiles(self):
        """Calculate volume profiles for all symbols"""
        try:
            logger.info("Calculating Volume Profiles for all symbols...")

            calculated_count = 0
            for symbol in self.trading_symbols:
                vp_data = None

                if self.strategy_config.vp_period == VolumeProfilePeriod.DAILY:
                    # Use previous day's data
                    yesterday = datetime.now().replace(hour=0, minute=0) - timedelta(days=1)
                    vp_data = self.vp_calculator.calculate_daily_volume_profile(symbol, yesterday)

                elif self.strategy_config.vp_period == VolumeProfilePeriod.SESSION:
                    # Use current session data
                    vp_data = self.vp_calculator.calculate_session_volume_profile(symbol)

                if vp_data:
                    self.volume_profiles[symbol] = vp_data
                    calculated_count += 1

                    logger.debug(f"VP calculated for {symbol}: POC=Rs.{vp_data.poc:.2f}, "
                                 f"VAH=Rs.{vp_data.vah:.2f}, VAL=Rs.{vp_data.val:.2f}")

            self.vp_calculated = True
            logger.info(f"Volume Profiles calculated for {calculated_count}/{len(self.trading_symbols)} symbols")

        except Exception as e:
            logger.error(f"Error calculating volume profiles: {e}")

    async def scan_for_breakout_signals(self):
        """Scan for breakout signals based on detected breakouts"""
        try:
            if not self.breakout_detected:
                return

            logger.info(f"Processing {len(self.breakout_detected)} detected breakouts...")

            new_signals = []

            for symbol, breakout_type in list(self.breakout_detected.items()):
                # Skip if already have position
                if symbol in self.positions:
                    continue

                # Get data
                live_quote = self.live_quotes.get(symbol)
                vp_data = self.volume_profiles.get(symbol)

                if not live_quote or not vp_data:
                    continue

                # Evaluate the breakout
                signal = await self._evaluate_breakout_signal(
                    symbol, breakout_type, live_quote, vp_data
                )

                if signal:
                    new_signals.append(signal)

            # Sort signals by confidence
            new_signals.sort(key=lambda x: x.confidence, reverse=True)

            # Execute top signals
            available_slots = self.strategy_config.max_positions - len(self.positions)
            for signal in new_signals[:available_slots]:
                if signal.confidence >= self.strategy_config.min_confidence:
                    await self._execute_signal(signal)

        except Exception as e:
            logger.error(f"Error scanning for breakout signals: {e}")

    async def _evaluate_breakout_signal(
            self,
            symbol: str,
            breakout_type: str,
            live_quote: LiveQuote,
            vp_data: VolumeProfileData
    ) -> Optional[VolumeProfileSignal]:
        """Evaluate a breakout signal"""
        try:
            current_price = live_quote.ltp

            # Determine signal type and breakout level
            if breakout_type == "VAH":
                signal_type = SignalType.LONG
                breakout_level = vp_data.vah
                entry_price = current_price
                stop_loss = vp_data.poc  # Use POC as support
                target_price = entry_price + (entry_price - stop_loss) * self.strategy_config.target_multiplier
            else:  # VAL
                signal_type = SignalType.SHORT
                breakout_level = vp_data.val
                entry_price = current_price
                stop_loss = vp_data.poc  # Use POC as resistance
                target_price = entry_price - (stop_loss - entry_price) * self.strategy_config.target_multiplier

            # Calculate distance from POC
            distance_from_poc_pct = abs(entry_price - vp_data.poc) / vp_data.poc * 100

            # Check minimum distance from POC
            if distance_from_poc_pct < self.strategy_config.min_poc_distance_pct:
                logger.debug(f"Signal rejected for {symbol}: too close to POC")
                return None

            # Check volume confirmation
            volume_ratio = 1.0  # Placeholder - would calculate from actual volume data

            if self.strategy_config.require_volume_confirmation:
                if volume_ratio < self.strategy_config.min_volume_ratio:
                    logger.debug(f"Signal rejected for {symbol}: insufficient volume")
                    return None

            # Check if near low volume node (avoid if configured)
            near_lvn = self.vp_calculator.is_near_volume_node(
                entry_price, vp_data.low_volume_nodes, threshold_pct=0.5
            )

            if self.strategy_config.avoid_low_volume_nodes and near_lvn:
                logger.debug(f"Signal rejected for {symbol}: near low volume node")
                return None

            # Check if near high volume node (prefer)
            near_hvn = self.vp_calculator.is_near_volume_node(
                entry_price, vp_data.high_volume_nodes, threshold_pct=0.5
            )

            # Calculate confidence score
            confidence = self._calculate_signal_confidence(
                vp_data, entry_price, volume_ratio, near_hvn, near_lvn, distance_from_poc_pct
            )

            # Risk metrics
            risk_amount = abs(entry_price - stop_loss)
            reward_amount = abs(target_price - entry_price)

            # Create signal
            signal = create_vp_signal_from_symbol(
                symbol=symbol,
                signal_type=signal_type,
                vp_data=vp_data,
                breakout_level=breakout_level,
                breakout_type=f"{breakout_type}_BREAKOUT",
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                confidence=confidence,
                volume_ratio=volume_ratio,
                breakout_volume=live_quote.volume,
                distance_from_poc_pct=distance_from_poc_pct,
                near_hvn=near_hvn,
                near_lvn=near_lvn,
                timestamp=datetime.now(),
                vp_calculation_time=vp_data.end_time,
                risk_amount=risk_amount,
                reward_amount=reward_amount
            )

            logger.info(f"VP Signal: {symbol} {signal_type.value} - "
                        f"Entry: Rs.{entry_price:.2f}, SL: Rs.{stop_loss:.2f}, "
                        f"Target: Rs.{target_price:.2f}, Confidence: {confidence:.2f}")

            return signal

        except Exception as e:
            logger.error(f"Error evaluating breakout signal for {symbol}: {e}")
            return None

    def _calculate_signal_confidence(
            self,
            vp_data: VolumeProfileData,
            entry_price: float,
            volume_ratio: float,
            near_hvn: bool,
            near_lvn: bool,
            distance_from_poc_pct: float
    ) -> float:
        """Calculate signal confidence score"""
        try:
            confidence = 0.0

            # Volume confirmation (30%)
            if volume_ratio >= 2.0:
                confidence += 0.30
            elif volume_ratio >= 1.5:
                confidence += 0.20
            elif volume_ratio >= 1.0:
                confidence += 0.10

            # Distance from POC (25%)
            if distance_from_poc_pct >= 2.0:
                confidence += 0.25
            elif distance_from_poc_pct >= 1.5:
                confidence += 0.20
            elif distance_from_poc_pct >= 1.0:
                confidence += 0.15

            # Volume node context (25%)
            if near_hvn:
                confidence += 0.25  # Good - near support/resistance
            elif not near_lvn:
                confidence += 0.15  # Neutral - not near gaps
            else:
                confidence += 0.05  # Poor - in low volume area

            # Profile quality (20%)
            if vp_data.poc_strength >= 2.0:
                confidence += 0.20  # Strong POC
            elif vp_data.poc_strength >= 1.5:
                confidence += 0.15
            else:
                confidence += 0.10

            return min(confidence, 1.0)

        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5

    async def _execute_signal(self, signal: VolumeProfileSignal) -> bool:
        """Execute a trading signal"""
        try:
            # Calculate position size
            risk_amount = self.strategy_config.portfolio_value * self.strategy_config.risk_per_trade_pct / 100
            price_risk = abs(signal.entry_price - signal.stop_loss)

            if price_risk <= 0:
                return False

            quantity = int(risk_amount / price_risk)

            if quantity <= 0:
                return False

            # Create position
            position = create_position_from_signal(
                signal=signal,
                quantity=quantity if signal.signal_type == SignalType.LONG else -quantity,
                order_id=f"VP_{signal.symbol}_{int(datetime.now().timestamp())}"
            )

            # Store position
            self.positions[signal.symbol] = position
            self.signals_generated_today.append(signal)

            logger.info(f"VP Position Opened: {signal.symbol} {signal.signal_type.value} - "
                        f"Qty: {abs(quantity)}, Entry: Rs.{signal.entry_price:.2f}, "
                        f"Breakout: {signal.breakout_type}")

            return True

        except Exception as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return False

    async def monitor_positions(self):
        """Monitor existing positions"""
        try:
            positions_to_close = []

            for symbol, position in self.positions.items():
                live_quote = self.live_quotes.get(symbol)
                if not live_quote:
                    continue

                current_price = live_quote.ltp

                # Check stop loss
                if self._should_exit_on_stop_loss(position, current_price):
                    breakout_type = "VAH_BREAKOUT" if position.signal_type == SignalType.LONG else "VAL_BREAKOUT"
                    positions_to_close.append((symbol, "STOP_LOSS", breakout_type))

                # Check target
                elif self._should_exit_on_target(position, current_price):
                    breakout_type = "VAH_BREAKOUT" if position.signal_type == SignalType.LONG else "VAL_BREAKOUT"
                    positions_to_close.append((symbol, "TARGET", breakout_type))

            # Close positions
            for symbol, reason, breakout_type in positions_to_close:
                await self._close_position(symbol, reason, breakout_type)

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

    def _should_exit_on_stop_loss(self, position: Position, current_price: float) -> bool:
        """Check if should exit on stop loss"""
        if position.signal_type == SignalType.LONG:
            return current_price <= position.current_stop_loss
        else:
            return current_price >= position.current_stop_loss

    def _should_exit_on_target(self, position: Position, current_price: float) -> bool:
        """Check if should exit on target"""
        if position.signal_type == SignalType.LONG:
            return current_price >= position.target_price
        else:
            return current_price <= position.target_price

    async def _close_position(self, symbol: str, reason: str, breakout_type: str):
        """Close a position"""
        try:
            position = self.positions[symbol]
            current_price = self.live_quotes[symbol].ltp

            # Create trade result
            trade_result = create_trade_result_from_position(
                position, current_price, reason, breakout_type
            )

            # Store completed trade
            self.completed_trades.append(trade_result)

            # Update daily P&L
            self.daily_pnl += trade_result.net_pnl

            # Remove position
            del self.positions[symbol]

            logger.info(f"Position Closed: {symbol} - {reason} - P&L: Rs.{trade_result.net_pnl:.2f}")

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")

    def _update_market_state(self):
        """Update market state"""
        self.market_state.timestamp = datetime.now()
        self.market_state.vp_calculated = self.vp_calculated
        self.market_state.max_positions_reached = len(self.positions) >= self.strategy_config.max_positions
        self.market_state.daily_loss_limit_hit = self.daily_pnl < -abs(self.max_daily_loss)

    async def run_strategy_cycle(self):
        """Main strategy execution cycle"""
        try:
            self._update_market_state()

            # Calculate VP if not done
            if not self.vp_calculated:
                await self.calculate_volume_profiles()

            # Monitor positions
            await self.monitor_positions()

            # Scan for new signals
            if len(self.positions) < self.strategy_config.max_positions:
                await self.scan_for_breakout_signals()

            # Log status periodically
            if datetime.now().minute % 5 == 0:
                self._log_strategy_status()

        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")

    def _log_strategy_status(self):
        """Log current strategy status"""
        try:
            total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())

            logger.info(f"VP Strategy Status:")
            logger.info(f"  Positions: {len(self.positions)}/{self.strategy_config.max_positions}")
            logger.info(f"  Daily P&L: Rs.{self.daily_pnl:.2f}")
            logger.info(f"  Unrealized P&L: Rs.{total_unrealized:.2f}")
            logger.info(f"  VP Calculated: {self.vp_calculated}")
            logger.info(f"  Breakouts Detected: {len(self.breakout_detected)}")
            logger.info(f"  Signals Today: {len(self.signals_generated_today)}")

        except Exception as e:
            logger.error(f"Error logging status: {e}")