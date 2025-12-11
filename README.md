# Crypto Technical Scanner

A comprehensive cryptocurrency technical analysis scanner built with FastAPI and React, featuring real-time market data from Binance and 15+ technical indicators.

## Features

- **Real-time Market Data**: Fetches live data from Binance exchange using CCXT library
- **15+ Technical Indicators**: 
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - EMA (Exponential Moving Averages) - 9, 50 periods
  - Bollinger Bands
  - Stochastic Oscillator
  - ATR (Average True Range)
  - ADX (Average Directional Index)
  - CCI (Commodity Channel Index)
  - ROC (Rate of Change)
  - OBV (On-Balance Volume)
  - Williams %R
  - MFI (Money Flow Index)
  - Parabolic SAR
  - Supertrend
  - Ichimoku Cloud

- **Smart Signal Generation**: Automated buy/sell signals based on indicator analysis
- **Sentiment Scoring**: Composite sentiment score combining multiple indicators
- **Fundamental Analysis**: Market cap rank, sector classification, security scores
- **Modern React UI**: Beautiful, responsive interface with real-time updates
- **Coin Selection**: Dropdown to quickly view detailed analysis for specific coins

## Supported Coins

- BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT
- ADA/USDT, DOGE/USDT, AVAX/USDT, DOT/USDT
- LTC/USDT, LINK/USDT, UNI/USDT, ATOM/USDT, ETC/USDT

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Scanner
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the application**:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Access the application**:
Open your browser and navigate to `http://localhost:8000`

## Project Structure

```
Scanner/
├── app/
│   ├── main.py          # FastAPI application and endpoints
│   ├── scanner.py       # Core scanner logic and indicator calculations
│   └── static/
│       └── index.html    # React frontend
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## API Endpoints

- `GET /` - Serves the main web interface
- `GET /api/scan` - Fetches and analyzes market data for all configured symbols
- `GET /api/health` - Health check endpoint

## Technical Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React (via CDN)
- **Data Source**: Binance Exchange (via CCXT)
- **Technical Analysis**: pandas_ta
- **Data Processing**: pandas, numpy

## Configuration

You can modify the following in `app/scanner.py`:

- **Symbols**: Edit the `self.symbols` list to add/remove coins
- **Timeframe**: Change `self.timeframe` (default: '1h')
- **Exchange**: Modify exchange settings in `__init__` method

## Error Handling

The application includes comprehensive error handling:
- Graceful handling of missing data
- Dynamic indicator column detection
- Robust error logging
- Continues processing even if individual coins fail

## Future Enhancements

- Real-time WebSocket updates
- Historical data analysis
- Custom indicator combinations
- Alert system for specific conditions
- Integration with CoinGecko/CoinMarketCap for real fundamental data
- User authentication and saved watchlists
- Chart visualization with TradingView integration

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

