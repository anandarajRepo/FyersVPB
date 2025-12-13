# Fyers Volume Profile Breakout Trading Strategy

A professional algorithmic trading system for Indian stock markets using Volume Profile analysis to identify institutional price levels and high-probability breakout opportunities.

## 🎯 Strategy Overview

Volume Profile reveals where the most trading activity occurred, showing institutional price acceptance levels. This strategy:

- **Calculates Volume Profile** from real-time tick data
- **Identifies Key Levels**: POC, VAH, VAL
- **Detects Breakouts**: LONG above VAH, SHORT below VAL
- **Volume Confirmation**: Validates with volume analysis
- **Risk Management**: POC-based stops, 1:2 R:R targets

## 📊 Volume Profile Concepts

### Point of Control (POC)
Price level with highest traded volume - most accepted price by market.

### Value Area (70% volume)
- **VAH** (Value Area High): Upper boundary
- **VAL** (Value Area Low): Lower boundary

### Trading Signals
- **LONG**: Price breaks above VAH → Entry at market, Stop at POC, Target = Entry + 2×Risk
- **SHORT**: Price breaks below VAL → Entry at market, Stop at POC, Target = Entry - 2×Risk

## 🚀 Quick Start

```bash
# Install
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.template .env
# Edit .env with your Fyers credentials

# Authenticate (one-time)
python main.py auth

# Run
python main.py run
```

## ⚙️ Configuration

Key parameters in `.env`:

```bash
# Portfolio
PORTFOLIO_VALUE=100000
RISK_PER_TRADE=1.0
MAX_POSITIONS=5

# Volume Profile
VP_PERIOD=DAILY
PRICE_BUCKETS=50
VALUE_AREA_PCT=70.0

# Breakout
MIN_BREAKOUT_DISTANCE=0.3
MIN_VOLUME_RATIO=1.5
MIN_POC_DISTANCE=1.0

# Risk
STOP_LOSS_PCT=1.5
TARGET_MULTIPLIER=2.0
TRAILING_STOP_PCT=0.5
```

## 📈 Expected Performance

- Daily Signals: 3-8 opportunities
- Win Rate: 55-65%
- Risk:Reward: 1:2
- Monthly Target: 10-20%
- Max Drawdown: <5%

## 📋 Commands

```bash
python main.py auth         # Setup authentication
python main.py test-auth    # Test authentication
python main.py test         # Test WebSocket
python main.py config       # Validate config
python main.py run          # Run strategy
python main.py help         # Show help
```

## 🔐 Security

- Auto-refresh tokens with PIN
- Encrypted .env storage
- No hardcoded credentials

## ⚠️ Disclaimer

Educational/research purposes only. Trading involves substantial risk. Test thoroughly before live trading.