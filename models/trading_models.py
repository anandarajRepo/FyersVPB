# models/trading_models.py

"""
Trading Models for Volume Profile Breakout Strategy
Comprehensive data models for Volume Profile analysis and trading
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from config.settings import SignalType


@dataclass
class LiveQuote:
    """Real-time quote data from WebSocket"""
    symbol: str
    ltp: float  # Last traded price
    open_price: float
    high_price: float
    low_price: float
    volume: int
    previous_close: float
    timestamp: datetime
    change: float = 0.0
    change_pct: float = 0.0

    def __post_init__(self):
        if self.previous_close > 0:
            self.change = self.ltp - self.previous_close
            self.change_pct = (self.change / self.previous_close) * 100


@dataclass
class VolumeProfileData:
    """Complete Volume Profile data for a symbol"""
    symbol: str

    # Key Volume Profile levels
    poc: float  # Point of Control (highest volume price)
    vah: float  # Value Area High
    val: float  # Value Area Low

    # Profile metrics
    profile_high: float  # Highest price in profile
    profile_low: float  # Lowest price in profile
    total_volume: int
    value_area_volume: int  # Volume in value area (typically 70%)

    # Volume distribution
    volume_by_price: Dict[float, int]  # Price -> Volume mapping
    price_levels: List[float]  # All price levels

    # High/Low Volume Nodes
    hvn_levels: List[float]  # High Volume Nodes (>=1.5x avg)
    lvn_levels: List[float]  # Low Volume Nodes (<=0.5x avg)

    # Profile quality metrics
    poc_strength: float  # POC volume / average volume
    profile_width: float  # VAH - VAL
    profile_width_pct: float  # (VAH - VAL) / POC * 100

    # Timing
    calculation_time: datetime
    data_start_time: datetime
    data_end_time: datetime
    num_ticks: int

    def get_volume_at_price(self, price: float, tolerance: float = 0.1) -> int:
        """Get volume at a specific price level (with tolerance)"""
        total_volume = 0
        for price_level, volume in self.volume_by_price.items():
            if abs(price_level - price) <= tolerance:
                total_volume += volume
        return total_volume

    def is_near_hvn(self, price: float, distance_pct: float = 0.5) -> bool:
        """Check if price is near a High Volume Node"""
        for hvn in self.hvn_levels:
            if abs(price - hvn) / hvn * 100 <= distance_pct:
                return True
        return False

    def is_near_lvn(self, price: float, distance_pct: float = 0.5) -> bool:
        """Check if price is near a Low Volume Node"""
        for lvn in self.lvn_levels:
            if abs(price - lvn) / lvn * 100 <= distance_pct:
                return True
        return False


@dataclass
class VolumeProfileSignal:
    """Volume Profile breakout signal"""
    symbol: str
    signal_type: SignalType  # LONG or SHORT

    # Volume Profile context
    vp_data: VolumeProfileData
    breakout_level: float  # VAH for LONG, VAL for SHORT

    # Entry parameters
    entry_price: float
    stop_loss: float  # Typically at POC
    target_price: float

    # Signal quality metrics
    confidence: float  # Overall confidence score (0-1)
    volume_confirmation: float  # Volume ratio score
    poc_distance: float  # Distance from POC (%)
    near_hvn: bool  # Is breakout near High Volume Node
    near_lvn: bool  # Is breakout near Low Volume Node

    # Breakout metrics
    breakout_volume: int
    volume_ratio: float  # Current vs average volume
    breakout_distance_pct: float  # How far from VAH/VAL

    # Risk metrics
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float = field(init=False)

    # Timing
    timestamp: datetime
    vp_calculation_time: datetime

    def __post_init__(self):
        if self.risk_amount > 0:
            self.risk_reward_ratio = self.reward_amount / self.risk_amount


@dataclass
class Position:
    """Active trading position with Volume Profile context"""
    symbol: str
    signal_type: SignalType

    # Position details
    entry_price: float
    quantity: int
    stop_loss: float
    target_price: float

    # Volume Profile context
    vp_poc: float  # POC at entry
    vp_vah: float  # VAH at entry
    vp_val: float  # VAL at entry
    breakout_level: float  # Entry breakout level

    # Timing
    entry_time: datetime
    signal_time: datetime

    # Dynamic tracking
    current_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 0.0
    current_stop_loss: float = 0.0

    # Orders
    order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    target_order_id: Optional[str] = None

    # Performance
    unrealized_pnl: float = 0.0
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0

    def __post_init__(self):
        self.current_stop_loss = self.stop_loss
        self.highest_price = self.entry_price if self.signal_type == SignalType.LONG else 0.0
        self.lowest_price = self.entry_price if self.signal_type == SignalType.SHORT else float('inf')

    def update_price_extremes(self, current_price: float):
        """Update price extremes for trailing stops"""
        self.current_price = current_price

        if self.signal_type == SignalType.LONG:
            self.highest_price = max(self.highest_price, current_price)
            self.max_favorable_excursion = max(
                self.max_favorable_excursion,
                current_price - self.entry_price
            )
            self.max_adverse_excursion = min(
                self.max_adverse_excursion,
                current_price - self.entry_price
            )
        else:  # SHORT
            self.lowest_price = min(self.lowest_price, current_price)
            self.max_favorable_excursion = max(
                self.max_favorable_excursion,
                self.entry_price - current_price
            )
            self.max_adverse_excursion = min(
                self.max_adverse_excursion,
                self.entry_price - current_price
            )


@dataclass
class TradeResult:
    """Completed trade result with Volume Profile metrics"""
    symbol: str
    signal_type: SignalType

    # Trade details
    entry_price: float
    exit_price: float
    quantity: int

    # Timing
    entry_time: datetime
    exit_time: datetime
    holding_period: float  # in minutes

    # Volume Profile context
    entry_poc: float
    entry_vah: float
    entry_val: float
    breakout_level: float

    # Exit details
    exit_reason: str  # "TARGET", "STOP_LOSS", "TRAILING_STOP", "TIME_EXIT", "POC_RETEST"

    # Performance
    gross_pnl: float
    net_pnl: float = field(init=False)
    commission: float = 0.0

    # Extremes
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0

    def __post_init__(self):
        self.net_pnl = self.gross_pnl - self.commission
        self.holding_period = (self.exit_time - self.entry_time).total_seconds() / 60


@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # P&L metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0

    # Risk metrics
    max_drawdown: float = 0.0
    max_portfolio_risk: float = 0.0

    # Volume Profile specific
    vah_breakout_trades: int = 0
    val_breakout_trades: int = 0
    vah_win_rate: float = 0.0
    val_win_rate: float = 0.0
    avg_poc_distance: float = 0.0

    # Timing metrics
    avg_holding_period: float = 0.0

    # Recent performance
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0

    def update_metrics(self, trades: List[TradeResult]):
        """Update metrics from trade list"""
        if not trades:
            return

        self.total_trades = len(trades)
        self.winning_trades = sum(1 for t in trades if t.net_pnl > 0)
        self.losing_trades = self.total_trades - self.winning_trades
        self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0

        self.total_pnl = sum(t.net_pnl for t in trades)
        self.gross_profit = sum(t.net_pnl for t in trades if t.net_pnl > 0)
        self.gross_loss = sum(t.net_pnl for t in trades if t.net_pnl < 0)

        # Volume Profile specific metrics
        vah_trades = [t for t in trades if t.signal_type == SignalType.LONG]
        val_trades = [t for t in trades if t.signal_type == SignalType.SHORT]

        self.vah_breakout_trades = len(vah_trades)
        self.val_breakout_trades = len(val_trades)

        if self.vah_breakout_trades > 0:
            self.vah_win_rate = (sum(1 for t in vah_trades if t.net_pnl > 0) / self.vah_breakout_trades) * 100

        if self.val_breakout_trades > 0:
            self.val_win_rate = (sum(1 for t in val_trades if t.net_pnl > 0) / self.val_breakout_trades) * 100

        # Timing metrics
        if trades:
            self.avg_holding_period = sum(t.holding_period for t in trades) / len(trades)

            # Calculate average POC distance
            poc_distances = []
            for t in trades:
                poc_distance = abs(t.entry_price - t.entry_poc) / t.entry_poc * 100
                poc_distances.append(poc_distance)
            self.avg_poc_distance = sum(poc_distances) / len(poc_distances) if poc_distances else 0


@dataclass
class MarketState:
    """Current market state for strategy decisions"""
    timestamp: datetime

    # Market indicators
    market_trend: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    volatility_regime: str = "NORMAL"  # HIGH, NORMAL, LOW

    # Volume indicators
    market_volume_ratio: float = 1.0

    # Volume Profile state
    vp_calculation_active: bool = False
    vp_ready: bool = False
    signal_generation_active: bool = True

    # Risk indicators
    max_positions_reached: bool = False
    daily_loss_limit_hit: bool = False


# Helper Functions for Creating Model Instances

def create_vp_signal_from_symbol(
        symbol: str,
        signal_type: SignalType,
        vp_data: 'VolumeProfileData',
        breakout_level: float,
        breakout_type: str,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        confidence: float,
        volume_ratio: float,
        breakout_volume: int,
        distance_from_poc_pct: float,
        near_hvn: bool,
        near_lvn: bool,
        timestamp: datetime,
        vp_calculation_time: datetime,
        risk_amount: float,
        reward_amount: float
) -> VolumeProfileSignal:
    """
    Create a VolumeProfileSignal from symbol and market data.

    Args:
        symbol: Trading symbol
        signal_type: LONG or SHORT
        vp_data: Volume Profile data
        breakout_level: VAH or VAL level that was broken
        breakout_type: Type of breakout (e.g., "VAH_BREAKOUT")
        entry_price: Proposed entry price
        stop_loss: Stop loss price
        target_price: Target price
        confidence: Signal confidence (0-1)
        volume_ratio: Current volume vs average
        breakout_volume: Volume at breakout
        distance_from_poc_pct: Distance from POC as percentage
        near_hvn: Whether near high volume node
        near_lvn: Whether near low volume node
        timestamp: Signal generation timestamp
        vp_calculation_time: When VP was calculated
        risk_amount: Risk amount in price points
        reward_amount: Reward amount in price points

    Returns:
        VolumeProfileSignal instance
    """
    return VolumeProfileSignal(
        symbol=symbol,
        signal_type=signal_type,
        timestamp=timestamp,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=target_price,
        confidence=confidence,
        poc=vp_data.poc,
        vah=vp_data.vah,
        val=vp_data.val,
        breakout_level=breakout_level,
        breakout_type=breakout_type,
        volume_ratio=volume_ratio,
        breakout_volume=breakout_volume,
        distance_from_poc_pct=distance_from_poc_pct,
        near_hvn=near_hvn,
        near_lvn=near_lvn,
        vp_calculation_time=vp_calculation_time,
        risk_amount=risk_amount,
        reward_amount=reward_amount
    )


def create_position_from_signal(
        signal: VolumeProfileSignal,
        quantity: int,
        order_id: str
) -> Position:
    """
    Create a Position from a VolumeProfileSignal.

    Args:
        signal: The signal to convert to a position
        quantity: Position quantity (positive for LONG, negative for SHORT)
        order_id: Unique order identifier

    Returns:
        Position instance
    """
    return Position(
        symbol=signal.symbol,
        signal_type=signal.signal_type,
        entry_price=signal.entry_price,
        quantity=quantity,
        entry_time=signal.timestamp,
        target_price=signal.target_price,
        initial_stop_loss=signal.stop_loss,
        current_stop_loss=signal.stop_loss,
        order_id=order_id,
        poc=signal.poc,
        vah=signal.vah,
        val=signal.val,
        breakout_level=signal.breakout_level,
        breakout_type=signal.breakout_type
    )


def create_trade_result_from_position(
        position: Position,
        exit_price: float,
        exit_reason: str,
        breakout_type: str,
        commission: float = 0.0
) -> TradeResult:
    """
    Create a TradeResult from a closed Position.

    Args:
        position: The position being closed
        exit_price: Exit price
        exit_reason: Reason for exit (e.g., "TARGET", "STOP_LOSS")
        breakout_type: Type of breakout that led to this trade
        commission: Trading commission (default: 0.0)

    Returns:
        TradeResult instance
    """
    # Calculate P&L
    if position.signal_type == SignalType.LONG:
        gross_pnl = (exit_price - position.entry_price) * position.quantity
    else:  # SHORT
        gross_pnl = (position.entry_price - exit_price) * abs(position.quantity)

    return TradeResult(
        symbol=position.symbol,
        signal_type=position.signal_type,
        entry_price=position.entry_price,
        exit_price=exit_price,
        quantity=position.quantity,
        entry_time=position.entry_time,
        exit_time=datetime.now(),
        holding_period=0.0,  # Will be calculated in __post_init__
        entry_poc=position.poc,
        entry_vah=position.vah,
        entry_val=position.val,
        breakout_level=position.breakout_level,
        exit_reason=exit_reason,
        gross_pnl=gross_pnl,
        commission=commission,
        max_favorable_excursion=position.max_favorable_excursion,
        max_adverse_excursion=position.max_adverse_excursion
    )