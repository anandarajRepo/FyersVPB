# config/symbols.py

"""
Centralized Symbol Configuration for Volume Profile Strategy
Single source of truth for symbol to Fyers format mapping
"""

from typing import Dict, List, Tuple


class VolumeProfileSymbolManager:
    """Centralized symbol manager for Volume Profile strategy"""

    def __init__(self):
        # Symbol mapping: display_symbol -> Fyers WebSocket format
        self._symbol_mappings: Dict[str, str] = {
            # Large Cap - High Liquidity (Best for Volume Profile)
            "RELIANCE": "NSE:RELIANCE-EQ",
            "TCS": "NSE:TCS-EQ",
            "HDFCBANK": "NSE:HDFCBANK-EQ",
            "INFY": "NSE:INFY-EQ",
            "ICICIBANK": "NSE:ICICIBANK-EQ",
            "HINDUNILVR": "NSE:HINDUNILVR-EQ",
            "ITC": "NSE:ITC-EQ",
            "SBIN": "NSE:SBIN-EQ",
            "BHARTIARTL": "NSE:BHARTIARTL-EQ",
            "KOTAKBANK": "NSE:KOTAKBANK-EQ",

            # IT Sector
            "WIPRO": "NSE:WIPRO-EQ",
            "HCLTECH": "NSE:HCLTECH-EQ",
            "TECHM": "NSE:TECHM-EQ",
            "LTI": "NSE:LTI-EQ",

            # Banking & Financial
            "AXISBANK": "NSE:AXISBANK-EQ",
            "INDUSINDBK": "NSE:INDUSINDBK-EQ",
            "BAJFINANCE": "NSE:BAJFINANCE-EQ",
            "HDFCLIFE": "NSE:HDFCLIFE-EQ",

            # Auto Sector
            "MARUTI": "NSE:MARUTI-EQ",
            "TATAMOTORS": "NSE:TATAMOTORS-EQ",
            "M&M": "NSE:M&M-EQ",
            "BAJAJ-AUTO": "NSE:BAJAJ-AUTO-EQ",
            "HEROMOTOCO": "NSE:HEROMOTOCO-EQ",
            "EICHERMOT": "NSE:EICHERMOT-EQ",

            # FMCG
            "NESTLEIND": "NSE:NESTLEIND-EQ",
            "BRITANNIA": "NSE:BRITANNIA-EQ",
            "DABUR": "NSE:DABUR-EQ",
            "MARICO": "NSE:MARICO-EQ",
            "GODREJCP": "NSE:GODREJCP-EQ",
            "COLPAL": "NSE:COLPAL-EQ",

            # Pharma
            "SUNPHARMA": "NSE:SUNPHARMA-EQ",
            "DRREDDY": "NSE:DRREDDY-EQ",
            "CIPLA": "NSE:CIPLA-EQ",
            "DIVISLAB": "NSE:DIVISLAB-EQ",

            # Metals & Energy
            "TATASTEEL": "NSE:TATASTEEL-EQ",
            "JSWSTEEL": "NSE:JSWSTEEL-EQ",
            "HINDALCO": "NSE:HINDALCO-EQ",
            "COALINDIA": "NSE:COALINDIA-EQ",
            "ONGC": "NSE:ONGC-EQ",
            "BPCL": "NSE:BPCL-EQ",
            "IOC": "NSE:IOC-EQ",

            # Infrastructure & Power
            "NTPC": "NSE:NTPC-EQ",
            "POWERGRID": "NSE:POWERGRID-EQ",
            "LT": "NSE:LT-EQ",
            "ULTRACEMCO": "NSE:ULTRACEMCO-EQ",
        }

        # Create reverse mapping for quick lookups
        self._reverse_mappings = {v: k for k, v in self._symbol_mappings.items()}

    def get_fyers_symbol(self, symbol: str) -> str:
        """Get Fyers format symbol"""
        return self._symbol_mappings.get(symbol.upper())

    def get_display_symbol(self, fyers_symbol: str) -> str:
        """Get display symbol from Fyers format"""
        return self._reverse_mappings.get(fyers_symbol)

    def get_all_symbols(self) -> List[str]:
        """Get all available symbols"""
        return list(self._symbol_mappings.keys())

    def get_all_fyers_symbols(self) -> List[str]:
        """Get all symbols in Fyers format"""
        return list(self._symbol_mappings.values())

    def create_symbol_mappings(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Create forward and reverse mapping dictionaries"""
        return self._symbol_mappings.copy(), self._reverse_mappings.copy()

    def validate_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported"""
        return symbol.upper() in self._symbol_mappings

    def get_trading_universe_size(self) -> int:
        """Get total number of tradable symbols"""
        return len(self._symbol_mappings)

    def export_for_websocket(self) -> Dict[str, str]:
        """Export symbols in format suitable for WebSocket subscription"""
        return self._symbol_mappings.copy()

    def get_symbol_summary(self) -> Dict:
        """Get summary of symbol universe"""
        return {
            'total_symbols': len(self._symbol_mappings),
            'symbols': self.get_all_symbols(),
            'fyers_symbols': self.get_all_fyers_symbols()
        }


# Global symbol manager instance
symbol_manager = VolumeProfileSymbolManager()


# Convenience functions for easy access
def get_vp_symbols() -> List[str]:
    """Get all Volume Profile trading symbols (display format)"""
    return symbol_manager.get_all_symbols()


def get_vp_fyers_symbols() -> List[str]:
    """Get all VP symbols in Fyers WebSocket format"""
    return symbol_manager.get_all_fyers_symbols()


def convert_to_fyers_format(symbol: str) -> str:
    """Convert display symbol to Fyers format"""
    return symbol_manager.get_fyers_symbol(symbol)


def convert_from_fyers_format(fyers_symbol: str) -> str:
    """Convert Fyers format to display symbol"""
    return symbol_manager.get_display_symbol(fyers_symbol)


def validate_vp_symbol(symbol: str) -> bool:
    """Validate if symbol is supported for VP trading"""
    return symbol_manager.validate_symbol(symbol)


def get_symbol_mappings() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Get symbol mappings for WebSocket services"""
    return symbol_manager.create_symbol_mappings()


# Example usage
if __name__ == "__main__":
    print("Volume Profile Symbol Manager Test")
    print("=" * 50)

    print(f"Total symbols: {symbol_manager.get_trading_universe_size()}")

    # Test specific symbol
    test_symbol = "RELIANCE"
    fyers_format = convert_to_fyers_format(test_symbol)
    print(f"\nTesting {test_symbol}:")
    print(f"  Display: {test_symbol}")
    print(f"  Fyers: {fyers_format}")

    # Test reverse conversion
    display_format = convert_from_fyers_format(fyers_format)
    print(f"  Reverse: {display_format}")

    # Test validation
    print(f"\nValidation test:")
    print(f"  Valid symbol '{test_symbol}': {validate_vp_symbol(test_symbol)}")
    print(f"  Invalid symbol 'INVALID': {validate_vp_symbol('INVALID')}")

    # Display all symbols
    print(f"\nAll symbols ({symbol_manager.get_trading_universe_size()}):")
    for symbol in get_vp_symbols()[:10]:  # Show first 10
        print(f"  {symbol} -> {convert_to_fyers_format(symbol)}")
    print(f"  ... and {symbol_manager.get_trading_universe_size() - 10} more")