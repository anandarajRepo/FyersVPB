# config/settings.py

"""
Core Configuration Settings for Volume Profile Breakout Strategy
Centralized settings following FyersORB pattern
"""

import os
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class VolumeProfilePeriod(Enum):
    """Volume Profile calculation period"""
    DAILY = "DAILY"  # Full trading day profile
    SESSION = "SESSION"  # Specific session (morning/afternoon)
    ROLLING = "ROLLING"  # Rolling N-minute window


@dataclass
class FyersConfig:
    """Fyers API configuration"""
    client_id: str
    secret_key: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    pin: Optional[str] = None
    base_url: str = "https://api-t1.fyers.in/api/v3"


@dataclass
class VolumeProfileStrategyConfig:
    """Volume Profile Breakout Strategy Configuration"""

    # Portfolio settings
    portfolio_value: float = 100000  # ₹1 lakh
    risk_per_trade_pct: float = 1.0  # 1% risk per trade
    max_positions: int = 5

    # Volume Profile parameters
    vp_period: VolumeProfilePeriod = VolumeProfilePeriod.DAILY
    price_buckets: int = 50  # Number of price levels for VP calculation
    value_area_pct: float = 70.0  # Standard 70% value area
    rolling_window_minutes: int = 60  # For ROLLING period type

    # Breakout criteria
    min_breakout_distance_pct: float = 0.3  # Min distance from VAH/VAL
    min_volume_ratio: float = 1.5  # Current vs average volume
    min_poc_distance_pct: float = 1.0  # Min distance from POC

    # Signal filtering
    min_confidence: float = 0.65  # Minimum signal confidence (65%)
    require_volume_confirmation: bool = True  # Require volume confirmation
    avoid_low_volume_nodes: bool = True  # Skip breakouts near LVN
    prefer_high_volume_nodes: bool = True  # Prefer breakouts near HVN

    # Volume analysis parameters
    volume_ma_period: int = 20  # Volume moving average period
    high_volume_threshold: float = 1.5  # High volume threshold (1.5x average)
    low_volume_threshold: float = 0.5  # Low volume threshold (0.5x average)

    # Risk management
    stop_loss_pct: float = 1.5  # Stop loss from entry
    target_multiplier: float = 2.0  # Target as multiple of risk (1:2)
    trailing_stop_pct: float = 0.5  # Trailing stop adjustment
    use_poc_as_stop: bool = True  # Use POC level as stop loss

    # Position management
    enable_trailing_stops: bool = True
    enable_partial_exits: bool = True
    partial_exit_pct: float = 50.0  # Exit 50% at first target
    square_off_time: str = "15:20"  # Square off time (IST)


@dataclass
class TradingConfig:
    """Trading session configuration"""

    # Market hours (IST)
    market_start_hour: int = 9
    market_start_minute: int = 15
    market_end_hour: int = 15
    market_end_minute: int = 30

    # Volume Profile calculation timing
    vp_calculation_time_hour: int = 9  # VP calculation start hour
    vp_calculation_time_minute: int = 30  # VP calculation start minute
    vp_start_time: str = "09:15"  # Start calculating VP
    vp_ready_time: str = "10:00"  # VP ready for signals (45 min data)

    # Signal generation window
    signal_generation_start_hour: int = 9  # Signal generation start hour
    signal_generation_start_minute: int = 30  # Signal generation start minute
    signal_start_hour: int = 10
    signal_start_minute: int = 0
    signal_generation_end_hour: int = 14  # Signal generation end hour
    signal_generation_end_minute: int = 30  # Signal generation end minute
    signal_end_hour: int = 15
    signal_end_minute: int = 0

    # Monitoring intervals
    monitoring_interval: int = 10  # Strategy cycle (seconds)
    position_update_interval: int = 5  # Position monitoring (seconds)
    vp_update_interval: int = 300  # VP update interval (seconds)
    vp_recalc_interval: int = 300  # Recalculate VP every 5 minutes