#!/usr/bin/env python3
# test_tick_data.py

"""
Quick test to verify tick data collection is working
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

from services.fyers_market_data_service import FyersMarketDataService
from strategy.volume_profile_strategy import VolumeProfileBreakoutStrategy
from config.settings import FyersConfig, VolumeProfileStrategyConfig, TradingConfig, VolumeProfilePeriod

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_tick_data_collection():
    """Test that tick data is being collected properly"""

    print("\n" + "=" * 60)
    print("TICK DATA COLLECTION TEST")
    print("=" * 60)

    # Load environment
    load_dotenv()
    client_id = os.getenv('FYERS_CLIENT_ID')
    access_token = os.getenv('FYERS_ACCESS_TOKEN')

    if not client_id or not access_token:
        print("\n❌ Error: FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN must be set in .env")
        print("   Run 'python main.py auth' to setup authentication")
        return False

    # Create market data service
    print("\n✓ Creating market data service...")
    market_data_service = FyersMarketDataService(client_id, access_token)

    # Test connection
    print("✓ Testing Fyers API connection...")
    if not market_data_service.test_connection():
        print("\n❌ Failed to connect to Fyers API")
        return False

    print("✓ Connected to Fyers API")

    # Create strategy config
    fyers_config = FyersConfig(
        client_id=client_id,
        secret_key="",
        access_token=access_token,
        refresh_token=""
    )

    strategy_config = VolumeProfileStrategyConfig(
        portfolio_value=100000,
        risk_per_trade_pct=1.0,
        max_positions=5,
        vp_period=VolumeProfilePeriod.DAILY
    )

    trading_config = TradingConfig()

    # Create strategy
    print("✓ Creating strategy...")
    strategy = VolumeProfileBreakoutStrategy(
        fyers_config, strategy_config, trading_config
    )

    await strategy.initialize()

    # Connect market data to strategy
    market_data_service.add_quote_callback(strategy._on_live_data_update)
    print("✓ Market data connected to strategy")

    # Fetch quotes a few times
    print("\n✓ Fetching quotes (3 iterations)...")
    for i in range(3):
        print(f"\n  Iteration {i+1}/3:")
        quotes = market_data_service.fetch_quotes()
        print(f"    - Fetched {len(quotes)} quotes")

        # Check tick data in calculator
        total_ticks = sum(len(ticks) for ticks in strategy.vp_calculator.tick_data.values())
        symbols_with_data = len([s for s in strategy.trading_symbols
                                if strategy.vp_calculator.tick_data.get(s)])

        print(f"    - Total ticks collected: {total_ticks}")
        print(f"    - Symbols with tick data: {symbols_with_data}/{len(strategy.trading_symbols)}")
        print(f"    - Total quotes received by strategy: {strategy.total_quotes_received}")

        await asyncio.sleep(2)

    # Try to calculate volume profile for one symbol
    print("\n✓ Testing volume profile calculation...")

    # Find a symbol with data
    symbol_with_data = None
    for symbol in strategy.trading_symbols:
        if strategy.vp_calculator.tick_data.get(symbol):
            symbol_with_data = symbol
            break

    if symbol_with_data:
        print(f"  Testing with symbol: {symbol_with_data}")
        ticks = strategy.vp_calculator.tick_data.get(symbol_with_data, [])
        print(f"  Ticks available: {len(ticks)}")

        vp_data = strategy.vp_calculator.calculate_volume_profile(symbol_with_data)

        if vp_data:
            print(f"\n✅ SUCCESS! Volume profile calculated for {symbol_with_data}:")
            print(f"    POC: ₹{vp_data.poc:.2f}")
            print(f"    VAH: ₹{vp_data.vah:.2f}")
            print(f"    VAL: ₹{vp_data.val:.2f}")
            print(f"    Total Volume: {vp_data.total_volume:,}")
            print(f"    Num Ticks: {vp_data.num_ticks}")
        else:
            print(f"\n⚠️  Volume profile calculation returned None (might need more ticks)")
    else:
        print("\n⚠️  No symbols with tick data found")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    # Summary
    total_ticks = sum(len(ticks) for ticks in strategy.vp_calculator.tick_data.values())
    if total_ticks > 0:
        print(f"\n✅ Tick data collection is WORKING!")
        print(f"   Collected {total_ticks} ticks across {symbols_with_data} symbols")
        return True
    else:
        print(f"\n❌ Tick data collection is NOT working!")
        print(f"   No ticks were collected")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_tick_data_collection())
    exit(0 if success else 1)
