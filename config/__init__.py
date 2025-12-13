# config/__init__.py

"""
Configuration Package for Volume Profile Breakout Strategy
Provides all configuration classes and settings
"""

from .settings import (
    FyersConfig,
    VolumeProfileStrategyConfig,
    TradingConfig,
    SignalType,
    VolumeProfilePeriod
)

from .symbols import (
    symbol_manager,
    get_vp_symbols,
    get_vp_fyers_symbols,
    convert_to_fyers_format,
    convert_from_fyers_format,
    validate_vp_symbol,
    get_symbol_mappings
)

__version__ = "1.0.0"
__author__ = "Volume Profile Trading Strategy Team"

__all__ = [
    # Core configuration classes
    "FyersConfig",
    "VolumeProfileStrategyConfig",
    "TradingConfig",

    # Enums
    "SignalType",
    "VolumeProfilePeriod",

    # Symbol management
    "symbol_manager",
    "get_vp_symbols",
    "get_vp_fyers_symbols",
    "convert_to_fyers_format",
    "convert_from_fyers_format",
    "validate_vp_symbol",
    "get_symbol_mappings",
]