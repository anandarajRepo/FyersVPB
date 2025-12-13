# main.py

"""
Volume Profile Breakout Trading Strategy - Main Entry Point
Command-line interface for the trading strategy
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from config.settings import FyersConfig, VolumeProfileStrategyConfig, TradingConfig, VolumeProfilePeriod
from utils.enhanced_auth_helper import FyersAuthManager, setup_auth, test_authentication, update_pin
from strategy.volume_profile_strategy import VolumeProfileBreakoutStrategy

# Load environment variables
load_dotenv()


# Configure enhanced logging
def setup_logging():
    """Setup enhanced logging configuration"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging with rotation
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'vpb_strategy.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific log levels for external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('yfinance').setLevel(logging.WARNING)


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def load_configuration() -> tuple:
    """Load configuration from environment"""
    try:
        # Load .env file
        load_dotenv()

        # Fyers configuration
        fyers_config = FyersConfig(
            client_id=os.getenv('FYERS_CLIENT_ID'),
            secret_key=os.getenv('FYERS_SECRET_KEY'),
            access_token=os.getenv('FYERS_ACCESS_TOKEN'),
            refresh_token=os.getenv('FYERS_REFRESH_TOKEN')
        )

        # Strategy configuration
        strategy_config = VolumeProfileStrategyConfig(
            portfolio_value=float(os.getenv('PORTFOLIO_VALUE', '100000')),
            risk_per_trade_pct=float(os.getenv('RISK_PER_TRADE', '1.0')),
            max_positions=int(os.getenv('MAX_POSITIONS', '5')),
            vp_period=VolumeProfilePeriod(os.getenv('VP_PERIOD', 'DAILY')),
            price_buckets=int(os.getenv('PRICE_BUCKETS', '50')),
            value_area_pct=float(os.getenv('VALUE_AREA_PCT', '70.0')),
            min_breakout_distance_pct=float(os.getenv('MIN_BREAKOUT_DISTANCE', '0.3')),
            min_volume_ratio=float(os.getenv('MIN_VOLUME_RATIO', '1.5')),
            min_poc_distance_pct=float(os.getenv('MIN_POC_DISTANCE', '1.0')),
            min_confidence=float(os.getenv('MIN_CONFIDENCE', '0.65')),
            require_volume_confirmation=os.getenv('REQUIRE_VOLUME_CONFIRMATION', 'true').lower() == 'true',
            avoid_low_volume_nodes=os.getenv('AVOID_LOW_VOLUME_NODES', 'true').lower() == 'true',
            stop_loss_pct=float(os.getenv('STOP_LOSS_PCT', '1.5')),
            target_multiplier=float(os.getenv('TARGET_MULTIPLIER', '2.0')),
            trailing_stop_pct=float(os.getenv('TRAILING_STOP_PCT', '0.5')),
            enable_trailing_stops=os.getenv('ENABLE_TRAILING_STOPS', 'true').lower() == 'true',
            enable_partial_exits=os.getenv('ENABLE_PARTIAL_EXITS', 'true').lower() == 'true',
            partial_exit_pct=float(os.getenv('PARTIAL_EXIT_PCT', '50.0')),
            volume_ma_period=int(os.getenv('VOLUME_MA_PERIOD', '20')),
            high_volume_threshold=float(os.getenv('HIGH_VOLUME_THRESHOLD', '1.5')),
            low_volume_threshold=float(os.getenv('LOW_VOLUME_THRESHOLD', '0.5'))
        )

        # Trading configuration
        trading_config = TradingConfig(
            market_start_hour=int(os.getenv('MARKET_START_HOUR', '9')),
            market_start_minute=int(os.getenv('MARKET_START_MINUTE', '15')),
            market_end_hour=int(os.getenv('MARKET_END_HOUR', '15')),
            market_end_minute=int(os.getenv('MARKET_END_MINUTE', '30')),
            vp_calculation_time_hour=int(os.getenv('VP_CALCULATION_TIME_HOUR', '9')),
            vp_calculation_time_minute=int(os.getenv('VP_CALCULATION_TIME_MINUTE', '30')),
            signal_generation_start_hour=int(os.getenv('SIGNAL_GENERATION_START_HOUR', '9')),
            signal_generation_start_minute=int(os.getenv('SIGNAL_GENERATION_START_MINUTE', '30')),
            signal_generation_end_hour=int(os.getenv('SIGNAL_GENERATION_END_HOUR', '14')),
            signal_generation_end_minute=int(os.getenv('SIGNAL_GENERATION_END_MINUTE', '30')),
            monitoring_interval=int(os.getenv('MONITORING_INTERVAL', '10')),
            position_update_interval=int(os.getenv('POSITION_UPDATE_INTERVAL', '5')),
            vp_update_interval=int(os.getenv('VP_UPDATE_INTERVAL', '300'))
        )

        return fyers_config, strategy_config, trading_config

    except Exception as e:
        logger.error(f"Configuration loading failed: {e}")
        sys.exit(1)


def cmd_auth():
    """Setup authentication"""
    try:
        print("\n" + "=" * 60)
        print("FYERS API AUTHENTICATION SETUP")
        print("=" * 60)

        load_dotenv()
        client_id = os.getenv('FYERS_CLIENT_ID')
        secret_key = os.getenv('FYERS_SECRET_KEY')
        pin = os.getenv('FYERS_PIN')

        if not client_id or not secret_key:
            print("\n Error: FYERS_CLIENT_ID and FYERS_SECRET_KEY must be set in .env file")
            return

        # Setup authentication
        access_token, refresh_token = setup_auth(client_id, secret_key, pin)

        print("\n Authentication successful!")
        print(f"Access Token: {access_token[:20]}...")

    except Exception as e:
        print(f"\n Authentication failed: {e}")
        logger.error(f"Authentication error: {e}")


def cmd_test_auth():
    """Test authentication"""
    try:
        print("\n" + "=" * 60)
        print("TESTING AUTHENTICATION")
        print("=" * 60)

        load_dotenv()
        client_id = os.getenv('FYERS_CLIENT_ID')
        access_token = os.getenv('FYERS_ACCESS_TOKEN')

        if not client_id or not access_token:
            print("\n Error: Authentication not setup. Run 'python main.py auth' first")
            return

        if test_authentication(client_id, access_token):
            print("\n Authentication valid!")
        else:
            print("\n Authentication failed. Please run 'python main.py auth' again")

    except Exception as e:
        print(f"\n Test failed: {e}")
        logger.error(f"Test error: {e}")


def cmd_update_pin():
    """Update trading PIN"""
    try:
        print("\n" + "=" * 60)
        print("UPDATE TRADING PIN")
        print("=" * 60)

        pin = input("\nEnter your trading PIN: ").strip()
        update_pin(pin)

    except Exception as e:
        print(f"\n Update failed: {e}")
        logger.error(f"Update PIN error: {e}")


async def cmd_run():
    """Run the trading strategy"""
    try:
        print("\n" + "=" * 60)
        print("VOLUME PROFILE BREAKOUT STRATEGY")
        print("=" * 60)

        # Load configuration
        fyers_config, strategy_config, trading_config = load_configuration()

        # Validate authentication
        if not fyers_config.access_token:
            print("\n Error: Authentication not setup. Run 'python main.py auth' first")
            return

        # Create strategy
        strategy = VolumeProfileBreakoutStrategy(
            fyers_config, strategy_config, trading_config
        )

        # Initialize strategy
        if not await strategy.initialize():
            print("\n Strategy initialization failed")
            return

        print("\n Strategy initialized successfully!")
        print("\n Running strategy... (Press Ctrl+C to stop)")

        # Main execution loop
        while True:
            await strategy.run_strategy_cycle()
            await asyncio.sleep(trading_config.monitoring_interval)

    except KeyboardInterrupt:
        print("\n\n️  Strategy stopped by user")
    except Exception as e:
        print(f"\n Strategy error: {e}")
        logger.error(f"Strategy execution error: {e}")


async def cmd_test():
    """Test volume profile calculations"""
    try:
        print("\n" + "=" * 60)
        print("TESTING VOLUME PROFILE CALCULATIONS")
        print("=" * 60)

        # Load configuration
        fyers_config, strategy_config, trading_config = load_configuration()

        # Create strategy
        strategy = VolumeProfileBreakoutStrategy(
            fyers_config, strategy_config, trading_config
        )

        # Initialize
        await strategy.initialize()

        # Calculate volume profiles
        await strategy.calculate_volume_profiles()

        # Display results
        print(f"\n Volume Profiles Calculated: {len(strategy.volume_profiles)}")

        if strategy.volume_profiles:
            print("\n" + "=" * 60)
            print("SAMPLE VOLUME PROFILES")
            print("=" * 60)

            for symbol, vp_data in list(strategy.volume_profiles.items())[:5]:
                print(f"\n{symbol}:")
                print(f"  POC: Rs.{vp_data.poc:.2f} (Strength: {vp_data.poc_strength:.2f})")
                print(f"  VAH: Rs.{vp_data.vah:.2f}")
                print(f"  VAL: Rs.{vp_data.val:.2f}")
                print(f"  Profile Width: {vp_data.profile_width:.2f}%")
                print(f"  HVN Count: {len(vp_data.high_volume_nodes)}")
                print(f"  LVN Count: {len(vp_data.low_volume_nodes)}")

    except Exception as e:
        print(f"\n Test failed: {e}")
        logger.error(f"Test error: {e}")


def cmd_config():
    """Display current configuration"""
    try:
        print("\n" + "=" * 60)
        print("CURRENT CONFIGURATION")
        print("=" * 60)

        fyers_config, strategy_config, trading_config = load_configuration()

        print("\n Portfolio Settings:")
        print(f"  Portfolio Value: Rs.{strategy_config.portfolio_value:,.0f}")
        print(f"  Risk per Trade: {strategy_config.risk_per_trade_pct}%")
        print(f"  Max Positions: {strategy_config.max_positions}")

        print("\n Volume Profile Settings:")
        print(f"  VP Period: {strategy_config.vp_period.value}")
        print(f"  Price Buckets: {strategy_config.price_buckets}")
        print(f"  Value Area: {strategy_config.value_area_pct}%")

        print("\n Breakout Criteria:")
        print(f"  Min Breakout Distance: {strategy_config.min_breakout_distance_pct}%")
        print(f"  Min Volume Ratio: {strategy_config.min_volume_ratio}x")
        print(f"  Min POC Distance: {strategy_config.min_poc_distance_pct}%")

        print("\n Risk Management:")
        print(f"  Stop Loss: {strategy_config.stop_loss_pct}%")
        print(f"  Target Multiplier: {strategy_config.target_multiplier}x")
        print(f"  Trailing Stop: {strategy_config.trailing_stop_pct}%")

        print("\n Market Hours:")
        print(f"  Market: {trading_config.market_start_hour:02d}:{trading_config.market_start_minute:02d} - " +
              f"{trading_config.market_end_hour:02d}:{trading_config.market_end_minute:02d}")
        print(f"  VP Calculation: {trading_config.vp_calculation_time_hour:02d}:{trading_config.vp_calculation_time_minute:02d}")

    except Exception as e:
        print(f"\n Configuration display failed: {e}")
        logger.error(f"Config display error: {e}")


def cmd_status():
    """Display authentication status"""
    try:
        print("\n" + "=" * 60)
        print("AUTHENTICATION STATUS")
        print("=" * 60)

        load_dotenv()

        client_id = os.getenv('FYERS_CLIENT_ID')
        access_token = os.getenv('FYERS_ACCESS_TOKEN')
        token_expiry = os.getenv('FYERS_TOKEN_EXPIRY')

        print(f"\nClient ID: {' Set' if client_id else ' Not set'}")
        print(f"Access Token: {' Set' if access_token else ' Not set'}")
        print(f"Token Expiry: {token_expiry if token_expiry else ' Not set'}")

        if access_token:
            if test_authentication(client_id, access_token):
                print("\n Authentication is valid")
            else:
                print("\n Authentication is invalid or expired")
                print("   Run 'python main.py auth' to re-authenticate")

    except Exception as e:
        print(f"\n Status check failed: {e}")
        logger.error(f"Status check error: {e}")


def cmd_help():
    """Display help information"""
    print("\n" + "=" * 60)
    print("VOLUME PROFILE BREAKOUT STRATEGY - COMMANDS")
    print("=" * 60)
    print("\nAuthentication:")
    print("  auth          - Setup API authentication")
    print("  test-auth     - Test authentication")
    print("  update-pin    - Update trading PIN")
    print("  status        - Show authentication status")
    print("\nStrategy Operations:")
    print("  run           - Run the trading strategy")
    print("  test          - Test volume profile calculations")
    print("  config        - Display current configuration")
    print("\nInformation:")
    print("  help          - Display this help message")
    print("\nUsage:")
    print("  python main.py <command>")
    print("\nExample:")
    print("  python main.py auth")
    print("  python main.py run")
    print("")


def main():
    """Main entry point"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Parse command
    if len(sys.argv) < 2:
        cmd_help()
        return

    command = sys.argv[1].lower()

    # Execute command
    if command == 'auth':
        cmd_auth()
    elif command == 'test-auth':
        cmd_test_auth()
    elif command == 'update-pin':
        cmd_update_pin()
    elif command == 'run':
        asyncio.run(cmd_run())
    elif command == 'test':
        asyncio.run(cmd_test())
    elif command == 'config':
        cmd_config()
    elif command == 'status':
        cmd_status()
    elif command == 'help':
        cmd_help()
    else:
        print(f"\n Unknown command: {command}")
        print("   Run 'python main.py help' for available commands")


if __name__ == "__main__":
    main()