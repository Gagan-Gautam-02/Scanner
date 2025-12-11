# CCXT Live Data Integration

This document describes how the Crypto Scanner uses CCXT for fetching live cryptocurrency data from Binance.

## CCXT Configuration

### Exchange Setup
- **Exchange**: Binance (via `ccxt.async_support`)
- **Market Type**: Spot (for better compatibility)
- **Rate Limiting**: Enabled (`enableRateLimit: True`)
- **Timeout**: 30 seconds

### Key Features

1. **Async Support**: Uses `ccxt.async_support` for non-blocking operations
2. **Market Loading**: Automatically loads exchange markets on startup
3. **Concurrent Fetching**: Fetches data for all symbols simultaneously
4. **Error Handling**: Handles network errors, exchange errors, and rate limits gracefully

## Data Fetching Methods

### 1. OHLCV Data (`fetch_ohlcv`)
- Fetches historical candle data (Open, High, Low, Close, Volume)
- Default: 200 candles at 1h timeframe
- Automatically gets the most recent data
- Used for technical indicator calculations

### 2. Ticker Data (`fetch_ticker`)
- Fetches real-time ticker information
- Includes: last price, bid/ask, 24h high/low, volume, price change
- Used for displaying live prices

## API Endpoints

### `/api/scan`
Fetches OHLCV data, calculates indicators, and returns analysis for all configured symbols.

**Response includes:**
- Technical indicators (15+)
- Trading signals (BUY/SELL/NEUTRAL)
- Sentiment scores
- Live price data (from ticker)
- Fundamental analysis

### `/api/ticker/{symbol}`
Fetches live ticker data for a specific symbol.

**Example:**
```bash
GET /api/ticker/BTC/USDT
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTC/USDT",
    "last": 43250.50,
    "bid": 43249.00,
    "ask": 43251.00,
    "high": 43500.00,
    "low": 43000.00,
    "volume": 1234567.89,
    "change": 2.5,
    "timestamp": 1234567890
  }
}
```

## Data Flow

```
1. Application Startup
   └─> Load Binance markets (once)

2. User Requests Scan
   └─> Fetch OHLCV for all symbols (concurrent)
   └─> Fetch ticker for each symbol (concurrent)
   └─> Calculate indicators
   └─> Generate signals
   └─> Return combined analysis

3. Application Shutdown
   └─> Close exchange connections
```

## Error Handling

The scanner handles various error types:

- **NetworkError**: Network connectivity issues
- **ExchangeError**: Exchange-specific errors (invalid symbol, rate limits, etc.)
- **Data Errors**: Missing or insufficient data
- **Calculation Errors**: Indicator calculation failures

All errors are logged, and the scanner continues processing other symbols even if one fails.

## Performance Optimizations

1. **Concurrent Requests**: Uses `asyncio.gather()` to fetch all symbols simultaneously
2. **Market Caching**: Markets are loaded once and cached
3. **Rate Limiting**: Respects exchange rate limits automatically
4. **Error Recovery**: Continues processing even if individual requests fail

## Supported Symbols

Currently configured for 14 major cryptocurrencies:
- BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT
- ADA/USDT, DOGE/USDT, AVAX/USDT, DOT/USDT
- LTC/USDT, LINK/USDT, UNI/USDT, ATOM/USDT, ETC/USDT

## Adding More Symbols

To add more symbols, edit `app/scanner.py`:

```python
self.symbols = [
    'BTC/USDT', 'ETH/USDT',
    # Add your symbol here
    'NEW/USDT',
]
```

## Changing Exchange

To use a different exchange, modify the initialization in `app/scanner.py`:

```python
# For example, to use Coinbase Pro:
self.exchange = ccxt.coinbasepro({
    'enableRateLimit': True,
    'apiKey': 'your-api-key',  # Optional
    'secret': 'your-secret',   # Optional
})
```

Note: Different exchanges may have different symbol formats and available markets.

## Rate Limits

Binance has rate limits:
- **Weight-based**: Each endpoint has a weight
- **IP-based**: Limits per IP address
- **Order-based**: Limits for trading endpoints

The scanner uses `enableRateLimit: True` to automatically respect these limits.

## Testing

To test the CCXT integration:

```python
import asyncio
from app.scanner import CryptoScanner

async def test():
    scanner = CryptoScanner()
    await scanner.load_markets()
    
    # Test OHLCV fetch
    df = await scanner.fetch_ohlcv('BTC/USDT')
    print(f"Fetched {len(df)} candles")
    
    # Test ticker fetch
    ticker = await scanner.fetch_ticker('BTC/USDT')
    print(f"Live price: {ticker['last']}")
    
    await scanner.close()

asyncio.run(test())
```

## References

- [CCXT Documentation](https://docs.ccxt.com/)
- [CCXT GitHub](https://github.com/ccxt/ccxt)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/)

