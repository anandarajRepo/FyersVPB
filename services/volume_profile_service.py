# services/volume_profile_service.py

"""
Volume Profile Calculation Service
Core engine for calculating POC, VAH, VAL from tick-level market data
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from models.trading_models import LiveQuote, VolumeProfileData

logger = logging.getLogger(__name__)


class VolumeProfileCalculator:
    """
    Calculate Volume Profile from tick data

    Implements Time-Price-Opportunity (TPO) and Volume Profile calculations:
    1. Accumulate price/volume data
    2. Create price buckets
    3. Calculate volume distribution
    4. Identify POC (Point of Control)
    5. Calculate Value Area (70% volume)
    6. Detect HVN/LVN (High/Low Volume Nodes)
    """

    def __init__(self, num_price_levels: int = 50, value_area_pct: float = 70.0):
        """
        Initialize Volume Profile calculator

        Args:
            num_price_levels: Number of price buckets for profile
            value_area_pct: Percentage of volume for value area (typically 70%)
        """
        self.num_price_levels = num_price_levels
        self.value_area_pct = value_area_pct

        # Data storage
        self.tick_data: Dict[str, List[LiveQuote]] = defaultdict(list)
        self.calculated_profiles: Dict[str, VolumeProfileData] = {}

        logger.info(f"Volume Profile Calculator initialized - "
                    f"Price levels: {num_price_levels}, Value area: {value_area_pct}%")

    def add_tick_data(self, symbol: str, quote: LiveQuote):
        """Add tick data for a symbol"""
        self.tick_data[symbol].append(quote)

    def clear_tick_data(self, symbol: str):
        """Clear tick data for a symbol"""
        if symbol in self.tick_data:
            self.tick_data[symbol].clear()

    def calculate_volume_profile(self, symbol: str,
                                 start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None) -> Optional[VolumeProfileData]:
        """
        Calculate Volume Profile for a symbol

        Args:
            symbol: Symbol to calculate profile for
            start_time: Start time for data (None = use all data)
            end_time: End time for data (None = use all data)

        Returns:
            VolumeProfileData or None if insufficient data
        """
        try:
            # Get tick data for symbol
            ticks = self.tick_data.get(symbol, [])

            if not ticks:
                logger.warning(f"No tick data available for {symbol}")
                return None

            # Filter by time if specified
            if start_time or end_time:
                filtered_ticks = []
                for tick in ticks:
                    if start_time and tick.timestamp < start_time:
                        continue
                    if end_time and tick.timestamp > end_time:
                        continue
                    filtered_ticks.append(tick)
                ticks = filtered_ticks

            if len(ticks) < 10:  # Minimum data requirement
                logger.warning(f"Insufficient tick data for {symbol}: {len(ticks)} ticks")
                return None

            # Extract price and volume data
            prices = [tick.ltp for tick in ticks]
            volumes = [tick.volume for tick in ticks]

            # Calculate price range
            price_min = min(prices)
            price_max = max(prices)
            price_range = price_max - price_min

            if price_range == 0:
                logger.warning(f"No price movement for {symbol}")
                return None

            # Create price buckets
            bucket_size = price_range / self.num_price_levels
            price_levels = [price_min + i * bucket_size for i in range(self.num_price_levels + 1)]

            # Calculate volume distribution by price level
            volume_by_price = defaultdict(int)

            for price, volume in zip(prices, volumes):
                # Find which bucket this price falls into
                bucket_idx = min(int((price - price_min) / bucket_size), self.num_price_levels - 1)
                bucket_price = price_levels[bucket_idx]

                # Add volume to this price bucket
                # Use volume delta (change from previous tick)
                volume_by_price[bucket_price] += volume

            # Find POC (Point of Control) - price with maximum volume
            poc = max(volume_by_price.items(), key=lambda x: x[1])[0]
            poc_volume = volume_by_price[poc]

            # Calculate total volume
            total_volume = sum(volume_by_price.values())

            # Calculate Value Area (70% of volume around POC)
            vah, val, value_area_volume = self._calculate_value_area(
                volume_by_price, poc, total_volume
            )

            # Identify High and Low Volume Nodes
            avg_volume = total_volume / len(volume_by_price)
            hvn_levels = [price for price, vol in volume_by_price.items() if vol >= 1.5 * avg_volume]
            lvn_levels = [price for price, vol in volume_by_price.items() if vol <= 0.5 * avg_volume]

            # Calculate profile quality metrics
            poc_strength = poc_volume / avg_volume if avg_volume > 0 else 0
            profile_width = vah - val
            profile_width_pct = (profile_width / poc * 100) if poc > 0 else 0

            # Create VolumeProfileData object
            vp_data = VolumeProfileData(
                symbol=symbol,
                poc=poc,
                vah=vah,
                val=val,
                profile_high=price_max,
                profile_low=price_min,
                total_volume=total_volume,
                value_area_volume=value_area_volume,
                volume_by_price=dict(volume_by_price),
                price_levels=price_levels,
                hvn_levels=sorted(hvn_levels),
                lvn_levels=sorted(lvn_levels),
                poc_strength=poc_strength,
                profile_width=profile_width,
                profile_width_pct=profile_width_pct,
                calculation_time=datetime.now(),
                data_start_time=ticks[0].timestamp,
                data_end_time=ticks[-1].timestamp,
                num_ticks=len(ticks)
            )

            # Cache the calculated profile
            self.calculated_profiles[symbol] = vp_data

            logger.info(f"Volume Profile calculated for {symbol}: "
                        f"POC=₹{poc:.2f}, VAH=₹{vah:.2f}, VAL=₹{val:.2f}, "
                        f"Width={profile_width:.2f} ({profile_width_pct:.2f}%), "
                        f"Ticks={len(ticks)}")

            return vp_data

        except Exception as e:
            logger.error(f"Error calculating Volume Profile for {symbol}: {e}")
            return None

    def _calculate_value_area(self, volume_by_price: Dict[float, int],
                              poc: float, total_volume: int) -> Tuple[float, float, int]:
        """
        Calculate Value Area (VAH and VAL)

        Value Area contains 70% of total volume, expanding from POC

        Args:
            volume_by_price: Volume distribution
            poc: Point of Control
            total_volume: Total volume

        Returns:
            Tuple of (VAH, VAL, value_area_volume)
        """
        try:
            target_volume = total_volume * (self.value_area_pct / 100)

            # Sort prices
            sorted_prices = sorted(volume_by_price.keys())

            # Find POC index
            poc_idx = sorted_prices.index(poc)

            # Expand from POC until we reach target volume
            upper_idx = poc_idx
            lower_idx = poc_idx
            accumulated_volume = volume_by_price[poc]

            while accumulated_volume < target_volume:
                # Determine which direction to expand (higher volume)
                upper_volume = 0
                lower_volume = 0

                if upper_idx < len(sorted_prices) - 1:
                    upper_volume = volume_by_price[sorted_prices[upper_idx + 1]]

                if lower_idx > 0:
                    lower_volume = volume_by_price[sorted_prices[lower_idx - 1]]

                # Expand in direction with more volume
                if upper_volume >= lower_volume and upper_idx < len(sorted_prices) - 1:
                    upper_idx += 1
                    accumulated_volume += volume_by_price[sorted_prices[upper_idx]]
                elif lower_idx > 0:
                    lower_idx -= 1
                    accumulated_volume += volume_by_price[sorted_prices[lower_idx]]
                else:
                    # Can't expand further
                    break

            vah = sorted_prices[upper_idx]
            val = sorted_prices[lower_idx]

            return vah, val, accumulated_volume

        except Exception as e:
            logger.error(f"Error calculating Value Area: {e}")
            # Fallback: use price range
            sorted_prices = sorted(volume_by_price.keys())
            return sorted_prices[-1], sorted_prices[0], total_volume

    def get_cached_profile(self, symbol: str) -> Optional[VolumeProfileData]:
        """Get cached Volume Profile for symbol"""
        return self.calculated_profiles.get(symbol)

    def calculate_daily_volume_profile(self, symbol: str) -> Optional[VolumeProfileData]:
        """Calculate Volume Profile for current trading day"""
        today = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
        return self.calculate_volume_profile(symbol, start_time=today)

    def calculate_session_volume_profile(self, symbol: str,
                                         session_start: datetime,
                                         session_end: datetime) -> Optional[VolumeProfileData]:
        """Calculate Volume Profile for a specific session"""
        return self.calculate_volume_profile(symbol, start_time=session_start, end_time=session_end)

    def calculate_rolling_volume_profile(self, symbol: str,
                                         window_minutes: int = 60) -> Optional[VolumeProfileData]:
        """Calculate Volume Profile for rolling N-minute window"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=window_minutes)
        return self.calculate_volume_profile(symbol, start_time=start_time, end_time=end_time)

    def is_near_volume_node(self, vp_data: VolumeProfileData,
                            price: float, distance_pct: float = 0.5) -> Tuple[bool, str]:
        """
        Check if price is near a High or Low Volume Node

        Args:
            vp_data: Volume Profile data
            price: Price to check
            distance_pct: Distance threshold (%)

        Returns:
            Tuple of (is_near, node_type) where node_type is "HVN", "LVN", or "NONE"
        """
        # Check HVN
        if vp_data.is_near_hvn(price, distance_pct):
            return True, "HVN"

        # Check LVN
        if vp_data.is_near_lvn(price, distance_pct):
            return True, "LVN"

        return False, "NONE"

    def get_volume_profile_summary(self, symbol: str) -> Dict:
        """Get summary of Volume Profile for a symbol"""
        vp_data = self.get_cached_profile(symbol)

        if not vp_data:
            return {'error': 'No Volume Profile data available'}

        return {
            'symbol': symbol,
            'poc': vp_data.poc,
            'vah': vp_data.vah,
            'val': vp_data.val,
            'profile_width': vp_data.profile_width,
            'profile_width_pct': vp_data.profile_width_pct,
            'poc_strength': vp_data.poc_strength,
            'total_volume': vp_data.total_volume,
            'num_hvn': len(vp_data.hvn_levels),
            'num_lvn': len(vp_data.lvn_levels),
            'num_ticks': vp_data.num_ticks,
            'calculation_time': vp_data.calculation_time.strftime('%H:%M:%S')
        }


# Example usage
if __name__ == "__main__":
    print("Volume Profile Calculator Test")
    print("=" * 50)

    # Create calculator
    calculator = VolumeProfileCalculator(num_price_levels=50, value_area_pct=70.0)
    print(f"✓ Calculator initialized")

    # Simulate tick data
    import random

    base_price = 1000.0
    symbol = "RELIANCE"

    print(f"\nSimulating tick data for {symbol}...")
    for i in range(100):
        price = base_price + random.uniform(-5, 5)
        volume = random.randint(1000, 5000)

        tick = LiveQuote(
            symbol=symbol,
            ltp=price,
            open_price=base_price,
            high_price=price + random.uniform(0, 2),
            low_price=price - random.uniform(0, 2),
            volume=volume,
            previous_close=base_price,
            timestamp=datetime.now()
        )
        calculator.add_tick_data(symbol, tick)

    print(f"✓ Added {len(calculator.tick_data[symbol])} ticks")

    # Calculate Volume Profile
    print(f"\nCalculating Volume Profile...")
    vp_data = calculator.calculate_volume_profile(symbol)

    if vp_data:
        print(f"\n✓ Volume Profile calculated successfully:")
        print(f"  POC: ₹{vp_data.poc:.2f} (strength: {vp_data.poc_strength:.2f}x)")
        print(f"  VAH: ₹{vp_data.vah:.2f}")
        print(f"  VAL: ₹{vp_data.val:.2f}")
        print(f"  Profile Width: ₹{vp_data.profile_width:.2f} ({vp_data.profile_width_pct:.2f}%)")
        print(f"  Total Volume: {vp_data.total_volume:,}")
        print(f"  High Volume Nodes: {len(vp_data.hvn_levels)}")
        print(f"  Low Volume Nodes: {len(vp_data.lvn_levels)}")
        print(f"  Data Points: {vp_data.num_ticks}")

        # Test breakout detection
        print(f"\n✓ Testing breakout scenarios:")
        test_price = vp_data.vah + 1.0
        print(f"  Price above VAH (₹{test_price:.2f}): LONG signal opportunity")

        test_price = vp_data.val - 1.0
        print(f"  Price below VAL (₹{test_price:.2f}): SHORT signal opportunity")

        # Test volume node detection
        is_near, node_type = calculator.is_near_volume_node(vp_data, vp_data.poc, 0.5)
        print(f"  POC area node type: {node_type}")
    else:
        print(f"✗ Volume Profile calculation failed")

    print(f"\n✓ Test completed")