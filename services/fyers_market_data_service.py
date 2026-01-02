# services/fyers_market_data_service.py

"""
Fyers Market Data Service
Fetches live quotes from Fyers API and feeds them to the trading strategy
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from fyers_apiv3 import fyersModel

from models.trading_models import LiveQuote
from config.symbols import get_vp_fyers_symbols, convert_from_fyers_format

logger = logging.getLogger(__name__)


class FyersMarketDataService:
    """
    Market data service for fetching live quotes from Fyers API

    Features:
    - Fetches live quotes for all configured symbols
    - Converts Fyers API format to LiveQuote model
    - Supports callback-based data updates
    - Handles API errors gracefully
    """

    def __init__(self, client_id: str, access_token: str):
        """
        Initialize Fyers market data service

        Args:
            client_id: Fyers API client ID
            access_token: Fyers API access token
        """
        self.client_id = client_id
        self.access_token = access_token

        # Initialize Fyers Model
        self.fyers = fyersModel.FyersModel(
            client_id=client_id,
            is_async=False,
            token=access_token,
            log_path=""
        )

        # Get all symbols to fetch
        self.symbols = get_vp_fyers_symbols()

        # Callbacks for quote updates
        self.quote_callbacks: List[Callable[[str, LiveQuote], None]] = []

        # Cache for previous close prices (needed for volume calculation)
        self.previous_close_cache: Dict[str, float] = {}

        logger.info(f"Fyers Market Data Service initialized for {len(self.symbols)} symbols")

    def add_quote_callback(self, callback: Callable[[str, LiveQuote], None]):
        """
        Add a callback function to receive quote updates

        Args:
            callback: Function that takes (symbol, LiveQuote) as arguments
        """
        self.quote_callbacks.append(callback)
        logger.debug(f"Quote callback added. Total callbacks: {len(self.quote_callbacks)}")

    def fetch_quotes(self) -> Dict[str, LiveQuote]:
        """
        Fetch live quotes for all symbols from Fyers API

        Returns:
            Dictionary mapping symbol -> LiveQuote
        """
        try:
            # Prepare symbols payload
            # Fyers quotes API expects: {"symbols": "NSE:RELIANCE-EQ,NSE:TCS-EQ,..."}
            symbols_string = ",".join(self.symbols)

            # Fetch quotes
            response = self.fyers.quotes({"symbols": symbols_string})

            if response.get("code") != 200:
                logger.error(f"Failed to fetch quotes: {response.get('message', 'Unknown error')}")
                return {}

            # Parse response and convert to LiveQuote
            quotes = {}
            data = response.get("d", [])

            for quote_data in data:
                try:
                    live_quote = self._parse_quote(quote_data)
                    if live_quote:
                        # Get display symbol
                        display_symbol = convert_from_fyers_format(live_quote.symbol)
                        if display_symbol:
                            quotes[display_symbol] = live_quote

                            # Trigger callbacks
                            for callback in self.quote_callbacks:
                                try:
                                    callback(display_symbol, live_quote)
                                except Exception as e:
                                    logger.error(f"Error in quote callback for {display_symbol}: {e}")

                except Exception as e:
                    logger.error(f"Error parsing quote: {e}")
                    continue

            if quotes:
                logger.debug(f"Fetched {len(quotes)} quotes successfully")
            else:
                logger.warning("No quotes received from Fyers API")

            return quotes

        except Exception as e:
            logger.error(f"Error fetching quotes from Fyers API: {e}")
            return {}

    def _parse_quote(self, quote_data: Dict) -> Optional[LiveQuote]:
        """
        Parse Fyers API quote data to LiveQuote model

        Fyers quote format:
        {
            "n": "NSE:RELIANCE-EQ",
            "s": "ok",
            "v": {
                "ch": 12.5,           # Change
                "chp": 0.52,          # Change percentage
                "lp": 2412.50,        # Last price
                "spread": 0.05,
                "ask": 2412.50,
                "bid": 2412.45,
                "open_price": 2400.00,
                "high_price": 2415.00,
                "low_price": 2395.00,
                "prev_close_price": 2400.00,
                "volume": 1234567,
                "short_name": "RELIANCE",
                "exchange": "NSE",
                "description": "Reliance Industries Ltd",
                "original_name": "NSE:RELIANCE-EQ",
                "symbol": "NSE:RELIANCE-EQ",
                "fyToken": "10012345678",
                "tt": 1234567890       # Timestamp
            }
        }

        Args:
            quote_data: Raw quote data from Fyers API

        Returns:
            LiveQuote object or None if parsing fails
        """
        try:
            # Extract nested data
            symbol = quote_data.get("n", "")
            status = quote_data.get("s", "")

            if status != "ok":
                return None

            v = quote_data.get("v", {})

            # Get previous close for this symbol
            prev_close = v.get("prev_close_price", 0.0)
            if prev_close > 0:
                self.previous_close_cache[symbol] = prev_close
            else:
                # Use cached value if available
                prev_close = self.previous_close_cache.get(symbol, v.get("lp", 0.0))

            # Create LiveQuote
            live_quote = LiveQuote(
                symbol=symbol,
                ltp=v.get("lp", 0.0),
                open_price=v.get("open_price", 0.0),
                high_price=v.get("high_price", 0.0),
                low_price=v.get("low_price", 0.0),
                volume=v.get("volume", 0),
                previous_close=prev_close,
                timestamp=datetime.now(),  # Use current time
                change=v.get("ch", 0.0),
                change_pct=v.get("chp", 0.0)
            )

            return live_quote

        except Exception as e:
            logger.error(f"Error parsing quote data: {e}")
            return None

    def get_quote_for_symbol(self, symbol: str) -> Optional[LiveQuote]:
        """
        Fetch quote for a single symbol

        Args:
            symbol: Symbol in display format (e.g., "RELIANCE")

        Returns:
            LiveQuote or None if fetch fails
        """
        try:
            from config.symbols import convert_to_fyers_format

            fyers_symbol = convert_to_fyers_format(symbol)
            if not fyers_symbol:
                logger.warning(f"Invalid symbol: {symbol}")
                return None

            response = self.fyers.quotes({"symbols": fyers_symbol})

            if response.get("code") != 200:
                logger.error(f"Failed to fetch quote for {symbol}: {response.get('message')}")
                return None

            data = response.get("d", [])
            if data:
                return self._parse_quote(data[0])

            return None

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test connection to Fyers API

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch profile
            response = self.fyers.get_profile()

            if response.get("code") == 200:
                logger.info("Fyers API connection test successful")
                return True
            else:
                logger.error(f"Fyers API connection test failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Fyers API connection test error: {e}")
            return False


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    print("\n" + "=" * 60)
    print("FYERS MARKET DATA SERVICE TEST")
    print("=" * 60)

    # Load environment
    load_dotenv()
    client_id = os.getenv('FYERS_CLIENT_ID')
    access_token = os.getenv('FYERS_ACCESS_TOKEN')

    if not client_id or not access_token:
        print("\n❌ Error: FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN must be set in .env")
        exit(1)

    # Create service
    print("\n Creating market data service...")
    service = FyersMarketDataService(client_id, access_token)

    # Test connection
    print("\n Testing API connection...")
    if not service.test_connection():
        print("\n❌ Connection test failed")
        exit(1)

    print("\n✓ Connection test successful")

    # Fetch quotes
    print(f"\n Fetching quotes for {len(service.symbols)} symbols...")
    quotes = service.fetch_quotes()

    if quotes:
        print(f"\n✓ Fetched {len(quotes)} quotes successfully")
        print("\n" + "=" * 60)
        print("SAMPLE QUOTES")
        print("=" * 60)

        # Display first 5 quotes
        for symbol, quote in list(quotes.items())[:5]:
            print(f"\n{symbol}:")
            print(f"  LTP: ₹{quote.ltp:.2f}")
            print(f"  Change: ₹{quote.change:.2f} ({quote.change_pct:+.2f}%)")
            print(f"  Volume: {quote.volume:,}")
            print(f"  High: ₹{quote.high_price:.2f}")
            print(f"  Low: ₹{quote.low_price:.2f}")

        if len(quotes) > 5:
            print(f"\n... and {len(quotes) - 5} more")
    else:
        print("\n❌ No quotes fetched")

    print("\n✓ Test completed")
