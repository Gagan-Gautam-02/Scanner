import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
import logging
import numpy as np
import requests
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CryptoScanner:
    def __init__(self):
        # Initialize Binance exchange with proper configuration for live data
        self.exchange = ccxt.binance({
            'enableRateLimit': True,  # Respect rate limits
            'timeout': 30000,  # 30 second timeout
            'options': {
                'defaultType': 'spot',  # Use spot market for better compatibility
            }
        })
        self.symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
            'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 
            'LTC/USDT', 'LINK/USDT', 'UNI/USDT', 'ATOM/USDT', 'ETC/USDT'
        ]
        self.timeframe = '1h'  # Default timeframe
        self._markets_loaded = False
        
        # Indicator thresholds for buy/sell signals
        self.indicator_thresholds = {
            'RSI': {'oversold': 30, 'overbought': 70, 'neutral_low': 40, 'neutral_high': 60},
            'MACD': {'bullish_threshold': 0, 'bearish_threshold': 0},
            'Stochastic': {'oversold': 20, 'overbought': 80},
            'CCI': {'oversold': -100, 'overbought': 100},
            'MFI': {'oversold': 20, 'overbought': 80},
            'Williams_R': {'oversold': -80, 'overbought': -20},
            'ADX': {'weak': 25, 'strong': 50},
        }
    
    async def load_markets(self):
        """Load exchange markets - required for some operations"""
        if not self._markets_loaded:
            try:
                await self.exchange.load_markets()
                self._markets_loaded = True
                logger.info("Markets loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load markets: {e}")

    async def fetch_ohlcv(self, symbol, limit=200):
        """Fetch live OHLCV data from exchange using CCXT"""
        try:
            # Ensure markets are loaded
            if not self._markets_loaded:
                await self.load_markets()
            
            # Fetch live OHLCV data - CCXT automatically gets the most recent data
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol, 
                self.timeframe, 
                limit=limit,
                params={}  # Can add exchange-specific params here if needed
            )
            
            if not ohlcv or len(ohlcv) == 0:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Sort by timestamp to ensure chronological order (most recent last)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Ensure we have enough data for indicators
            if len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}: {len(df)} candles")
                return None
            
            logger.debug(f"Fetched {len(df)} candles for {symbol}, latest: {df.iloc[-1]['timestamp']}")
            return df
            
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching {symbol}: {e}")
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching data for {symbol}: {e}")
            return None
    
    async def fetch_ticker(self, symbol):
        """Fetch live ticker data for real-time price"""
        try:
            if not self._markets_loaded:
                await self.load_markets()
            
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'high': ticker.get('high'),
                'low': ticker.get('low'),
                'volume': ticker.get('quoteVolume'),
                'change': ticker.get('percentage'),
                'timestamp': ticker.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def fetch_orderbook(self, symbol, limit=20):
        """Fetch order book data to analyze market depth and order movements"""
        try:
            if not self._markets_loaded:
                await self.load_markets()
            
            orderbook = await self.exchange.fetch_order_book(symbol, limit=limit)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Calculate order book metrics
            total_bid_volume = sum([bid[1] for bid in bids]) if bids else 0
            total_ask_volume = sum([ask[1] for ask in asks]) if asks else 0
            
            # Calculate bid-ask spread
            best_bid = bids[0][0] if bids else None
            best_ask = asks[0][0] if asks else None
            spread = best_ask - best_bid if (best_bid and best_ask) else None
            spread_percentage = (spread / best_bid * 100) if spread and best_bid else None
            
            # Calculate order book imbalance
            imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) * 100 if (total_bid_volume + total_ask_volume) > 0 else 0
            
            # Analyze order concentration (top 5 levels)
            top5_bid_volume = sum([bid[1] for bid in bids[:5]]) if len(bids) >= 5 else total_bid_volume
            top5_ask_volume = sum([ask[1] for ask in asks[:5]]) if len(asks) >= 5 else total_ask_volume
            
            return {
                'symbol': symbol,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': spread,
                'spread_percentage': round(spread_percentage, 4) if spread_percentage else None,
                'total_bid_volume': round(total_bid_volume, 2),
                'total_ask_volume': round(total_ask_volume, 2),
                'order_imbalance': round(imbalance, 2),  # Positive = more buy pressure, Negative = more sell pressure
                'top5_bid_volume': round(top5_bid_volume, 2),
                'top5_ask_volume': round(top5_ask_volume, 2),
                'bid_ask_ratio': round(total_bid_volume / total_ask_volume, 2) if total_ask_volume > 0 else None,
                'timestamp': orderbook.get('timestamp'),
                'order_movement': 'Buy Pressure' if imbalance > 5 else 'Sell Pressure' if imbalance < -5 else 'Balanced'
            }
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return None
    
    def get_indicator_ranges(self, row):
        """Get indicator value ranges and their buy/sell signal zones"""
        ranges = {}
        
        try:
            # RSI Ranges
            rsi = row.get('RSI')
            if rsi is not None and not pd.isna(rsi):
                rsi_val = float(rsi)
                ranges['RSI'] = {
                    'value': round(rsi_val, 2),
                    'range': {'min': 0, 'max': 100},
                    'zones': {
                        'oversold': {'min': 0, 'max': self.indicator_thresholds['RSI']['oversold'], 'signal': 'BUY'},
                        'neutral_low': {'min': self.indicator_thresholds['RSI']['oversold'], 'max': self.indicator_thresholds['RSI']['neutral_low'], 'signal': 'WEAK BUY'},
                        'neutral': {'min': self.indicator_thresholds['RSI']['neutral_low'], 'max': self.indicator_thresholds['RSI']['neutral_high'], 'signal': 'NEUTRAL'},
                        'neutral_high': {'min': self.indicator_thresholds['RSI']['neutral_high'], 'max': self.indicator_thresholds['RSI']['overbought'], 'signal': 'WEAK SELL'},
                        'overbought': {'min': self.indicator_thresholds['RSI']['overbought'], 'max': 100, 'signal': 'SELL'}
                    },
                    'current_zone': self._get_rsi_zone(rsi_val)
                }
            
            # MACD Ranges
            macd = row.get('MACD_12_26_9')
            macd_signal = row.get('MACDs_12_26_9')
            if macd is not None and macd_signal is not None:
                if not pd.isna(macd) and not pd.isna(macd_signal):
                    macd_val = float(macd)
                    signal_val = float(macd_signal)
                    ranges['MACD'] = {
                        'value': round(macd_val, 4),
                        'signal_line': round(signal_val, 4),
                        'histogram': round(macd_val - signal_val, 4),
                        'signal': 'BULLISH' if macd_val > signal_val else 'BEARISH',
                        'strength': 'STRONG' if abs(macd_val - signal_val) > 0.5 else 'WEAK'
                    }
            
            # Stochastic Ranges
            stoch_k = row.get('STOCHk_14_3_3')
            if stoch_k is not None and not pd.isna(stoch_k):
                stoch_val = float(stoch_k)
                ranges['Stochastic'] = {
                    'value': round(stoch_val, 2),
                    'range': {'min': 0, 'max': 100},
                    'zones': {
                        'oversold': {'min': 0, 'max': self.indicator_thresholds['Stochastic']['oversold'], 'signal': 'BUY'},
                        'neutral': {'min': self.indicator_thresholds['Stochastic']['oversold'], 'max': self.indicator_thresholds['Stochastic']['overbought'], 'signal': 'NEUTRAL'},
                        'overbought': {'min': self.indicator_thresholds['Stochastic']['overbought'], 'max': 100, 'signal': 'SELL'}
                    },
                    'current_zone': 'oversold' if stoch_val < 20 else 'overbought' if stoch_val > 80 else 'neutral'
                }
            
            # CCI Ranges
            cci = row.get('CCI')
            if cci is not None and not pd.isna(cci):
                cci_val = float(cci)
                ranges['CCI'] = {
                    'value': round(cci_val, 2),
                    'range': {'min': -200, 'max': 200},
                    'zones': {
                        'oversold': {'min': -200, 'max': self.indicator_thresholds['CCI']['oversold'], 'signal': 'BUY'},
                        'neutral': {'min': self.indicator_thresholds['CCI']['oversold'], 'max': self.indicator_thresholds['CCI']['overbought'], 'signal': 'NEUTRAL'},
                        'overbought': {'min': self.indicator_thresholds['CCI']['overbought'], 'max': 200, 'signal': 'SELL'}
                    },
                    'current_zone': 'oversold' if cci_val < -100 else 'overbought' if cci_val > 100 else 'neutral'
                }
            
            # MFI Ranges
            mfi = row.get('MFI')
            if mfi is not None and not pd.isna(mfi):
                mfi_val = float(mfi)
                ranges['MFI'] = {
                    'value': round(mfi_val, 2),
                    'range': {'min': 0, 'max': 100},
                    'zones': {
                        'oversold': {'min': 0, 'max': self.indicator_thresholds['MFI']['oversold'], 'signal': 'BUY'},
                        'neutral': {'min': self.indicator_thresholds['MFI']['oversold'], 'max': self.indicator_thresholds['MFI']['overbought'], 'signal': 'NEUTRAL'},
                        'overbought': {'min': self.indicator_thresholds['MFI']['overbought'], 'max': 100, 'signal': 'SELL'}
                    },
                    'current_zone': 'oversold' if mfi_val < 20 else 'overbought' if mfi_val > 80 else 'neutral'
                }
            
            # ADX Strength
            adx = row.get('ADX_14')
            if adx is not None and not pd.isna(adx):
                adx_val = float(adx)
                ranges['ADX'] = {
                    'value': round(adx_val, 2),
                    'range': {'min': 0, 'max': 100},
                    'strength': 'Very Strong' if adx_val > 50 else 'Strong' if adx_val > 25 else 'Weak',
                    'trending': adx_val > 25
                }
            
            # Bollinger Bands Position
            close = row.get('close')
            lower_bb = None
            upper_bb = None
            for key in row.keys():
                if isinstance(key, str):
                    if key.startswith('BBL_'):
                        val = row[key]
                        if val is not None and not pd.isna(val):
                            lower_bb = float(val)
                    elif key.startswith('BBU_'):
                        val = row[key]
                        if val is not None and not pd.isna(val):
                            upper_bb = float(val)
            
            if close and lower_bb and upper_bb:
                bb_position = ((close - lower_bb) / (upper_bb - lower_bb)) * 100
                ranges['Bollinger_Bands'] = {
                    'price': round(float(close), 4),
                    'lower_band': round(lower_bb, 4),
                    'upper_band': round(upper_bb, 4),
                    'position_percentage': round(bb_position, 2),
                    'zones': {
                        'lower': {'min': 0, 'max': 20, 'signal': 'BUY'},
                        'middle': {'min': 20, 'max': 80, 'signal': 'NEUTRAL'},
                        'upper': {'min': 80, 'max': 100, 'signal': 'SELL'}
                    },
                    'current_zone': 'lower' if bb_position < 20 else 'upper' if bb_position > 80 else 'middle'
                }
                
        except Exception as e:
            logger.error(f"Error calculating indicator ranges: {e}")
        
        return ranges
    
    def _get_rsi_zone(self, rsi_val):
        """Get RSI zone name"""
        if rsi_val < self.indicator_thresholds['RSI']['oversold']:
            return 'oversold'
        elif rsi_val < self.indicator_thresholds['RSI']['neutral_low']:
            return 'neutral_low'
        elif rsi_val < self.indicator_thresholds['RSI']['neutral_high']:
            return 'neutral'
        elif rsi_val < self.indicator_thresholds['RSI']['overbought']:
            return 'neutral_high'
        else:
            return 'overbought'
    
    async def fetch_crypto_news(self, symbol=None, limit=5):
        """Fetch cryptocurrency news (using CryptoPanic API - free tier)"""
        try:
            base_asset = symbol.split('/')[0] if symbol else None
            
            # Using CryptoPanic free API (no key required for basic usage)
            # Alternative: You can use other free APIs or add API keys for more features
            url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                'auth_token': '',  # Optional: add token for more requests
                'public': 'true',
                'filter': 'hot',
                'currencies': base_asset if base_asset else 'BTC',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                news_items = []
                for item in data.get('results', [])[:limit]:
                    news_items.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'source': item.get('source', {}).get('title', 'Unknown'),
                        'published_at': item.get('published_at', ''),
                        'votes': item.get('votes', {}).get('positive', 0),
                        'sentiment': item.get('sentiment', 'neutral')
                    })
                return news_items
            else:
                # Fallback: Return sample news structure
                return [{
                    'title': f'Latest updates for {base_asset or "crypto markets"}',
                    'url': 'https://cryptopanic.com',
                    'source': 'CryptoPanic',
                    'published_at': datetime.now().isoformat(),
                    'sentiment': 'neutral',
                    'note': 'News API limit reached. Consider adding API key for more features.'
                }]
        except Exception as e:
            logger.warning(f"Could not fetch news: {e}")
            return []

    def calculate_indicators(self, df):
        """Calculate all technical indicators"""
        if df is None or df.empty or len(df) < 50:
            return None
        
        try:
            # Ensure no duplicate columns
            df = df.loc[:, ~df.columns.duplicated()].copy()
            
            # Ensure we have required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns: {required_cols}")
                return None

            # 1. RSI (Relative Strength Index)
            df['RSI'] = df.ta.rsi(length=14)

            # 2. MACD (Moving Average Convergence Divergence)
            macd = df.ta.macd(fast=12, slow=26, signal=9)
            if macd is not None and not macd.empty:
                df = pd.concat([df, macd], axis=1)

            # 3. EMA (Exponential Moving Average)
            ema_9 = df.ta.ema(length=9)
            if ema_9 is not None:
                if isinstance(ema_9, pd.DataFrame):
                    ema_9 = ema_9.iloc[:, 0]
                df['EMA_9'] = ema_9

            ema_50 = df.ta.ema(length=50)
            if ema_50 is not None:
                if isinstance(ema_50, pd.DataFrame):
                    ema_50 = ema_50.iloc[:, 0]
                df['EMA_50'] = ema_50

            # 4. Bollinger Bands
            bbands = df.ta.bbands(length=20, std=2)
            if bbands is not None and not bbands.empty:
                df = pd.concat([df, bbands], axis=1)

            # 5. Stochastic Oscillator
            stoch = df.ta.stoch(k=14, d=3, smooth_k=3)
            if stoch is not None and not stoch.empty:
                df = pd.concat([df, stoch], axis=1)

            # 6. ATR (Average True Range)
            atr = df.ta.atr(length=14)
            if atr is not None:
                df['ATR'] = atr

            # 7. ADX (Average Directional Index)
            adx = df.ta.adx(length=14)
            if adx is not None and not adx.empty:
                df = pd.concat([df, adx], axis=1)

            # 8. CCI (Commodity Channel Index)
            cci = df.ta.cci(length=14)
            if cci is not None:
                df['CCI'] = cci

            # 9. ROC (Rate of Change)
            roc = df.ta.roc(length=9)
            if roc is not None:
                df['ROC'] = roc

            # 10. OBV (On-Balance Volume)
            obv = df.ta.obv()
            if obv is not None:
                df['OBV'] = obv

            # 11. Williams %R
            willr = df.ta.willr(length=14)
            if willr is not None:
                df['WILLR'] = willr

            # 12. MFI (Money Flow Index)
            mfi = df.ta.mfi(length=14)
            if mfi is not None:
                df['MFI'] = mfi

            # 13. Parabolic SAR
            psar = df.ta.psar()
            if psar is not None and not psar.empty:
                df = pd.concat([df, psar], axis=1)

            # 14. Supertrend
            supertrend = df.ta.supertrend(length=10, multiplier=3)
            if supertrend is not None and not supertrend.empty:
                df = pd.concat([df, supertrend], axis=1)
            
            # 15. Ichimoku Cloud
            ichimoku = df.ta.ichimoku()
            if ichimoku is not None:
                if isinstance(ichimoku, tuple) and len(ichimoku) > 0:
                    df = pd.concat([df, ichimoku[0]], axis=1)
                elif not isinstance(ichimoku, tuple):
                    df = pd.concat([df, ichimoku], axis=1)

            # Get the latest row (most recent data)
            latest = df.iloc[-1].copy()
            
            # Convert any NaN values to None for JSON serialization
            latest = latest.replace([np.inf, -np.inf], np.nan)
            
            return latest
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_fundamental_data(self, symbol):
        """Get fundamental analysis data (placeholder - can be extended with real APIs)"""
        base_asset = symbol.split('/')[0]
        
        # Market cap rankings (approximate)
        market_cap_rank = {
            'BTC': 1, 'ETH': 2, 'BNB': 4, 'SOL': 5, 'XRP': 6,
            'ADA': 8, 'DOGE': 9, 'AVAX': 10, 'DOT': 13, 'LINK': 15,
            'LTC': 16, 'UNI': 17, 'ATOM': 18, 'ETC': 19
        }.get(base_asset, 99)
        
        return {
            'market_cap_rank': market_cap_rank,
            'market_dominance': "High" if market_cap_rank <= 5 else "Medium" if market_cap_rank <= 20 else "Low",
            'sector': "Layer 1" if base_asset in ['BTC', 'ETH', 'SOL', 'ADA', 'AVAX', 'DOT', 'ATOM'] else "DeFi" if base_asset in ['UNI', 'LINK'] else "Meme" if base_asset in ['DOGE'] else "Other",
            'github_activity': "Active",
            'security_score': "A+" if market_cap_rank <= 10 else "B" if market_cap_rank <= 20 else "C"
        }

    def analyze_sentiment_and_signal(self, row):
        """Analyze indicators and generate trading signals"""
        if row is None or pd.isna(row.get('close')):
            return None

        signals = []
        sentiment_score = 0.0

        try:
            close = float(row['close'])
            
            # RSI Logic
            rsi = row.get('RSI')
            if rsi is not None and not pd.isna(rsi):
                rsi = float(rsi)
                if rsi < 30:
                    signals.append("RSI Oversold (Buy)")
                    sentiment_score += 1.0
                elif rsi > 70:
                    signals.append("RSI Overbought (Sell)")
                    sentiment_score -= 1.0
            
            # MACD Logic
            macd_col = 'MACD_12_26_9'
            macds_col = 'MACDs_12_26_9'
            if macd_col in row and macds_col in row:
                macd_val = row[macd_col]
                macds_val = row[macds_col]
                if not pd.isna(macd_val) and not pd.isna(macds_val):
                    if float(macd_val) > float(macds_val):
                        signals.append("MACD Bullish Crossover")
                        sentiment_score += 1.0
                    elif float(macd_val) < float(macds_val):
                        signals.append("MACD Bearish Crossover")
                        sentiment_score -= 1.0

            # EMA Trend
            ema_50 = row.get('EMA_50')
            if ema_50 is not None and not pd.isna(ema_50):
                ema_50 = float(ema_50)
                if close > ema_50:
                    signals.append("Price above EMA 50 (Bullish)")
                    sentiment_score += 0.5
                elif close < ema_50:
                    signals.append("Price below EMA 50 (Bearish)")
                    sentiment_score -= 0.5

            # Bollinger Bands - Dynamic key finding
            lower_bb = None
            upper_bb = None
            
            for key in row.keys():
                if isinstance(key, str):
                    if key.startswith('BBL_'):
                        val = row[key]
                        if val is not None and not pd.isna(val):
                            lower_bb = float(val)
                    elif key.startswith('BBU_'):
                        val = row[key]
                        if val is not None and not pd.isna(val):
                            upper_bb = float(val)
            
            if lower_bb is not None and upper_bb is not None:
                if close < lower_bb:
                    signals.append("Price below Lower BB (Potential Buy)")
                    sentiment_score += 1.0
                elif close > upper_bb:
                    signals.append("Price above Upper BB (Potential Sell)")
                    sentiment_score -= 1.0

            # Stochastic
            stoch_k = row.get('STOCHk_14_3_3')
            if stoch_k is not None and not pd.isna(stoch_k):
                stoch_k = float(stoch_k)
                if stoch_k < 20:
                    signals.append("Stoch Oversold")
                    sentiment_score += 0.5
                elif stoch_k > 80:
                    signals.append("Stoch Overbought")
                    sentiment_score -= 0.5

            # ADX Strength
            adx = row.get('ADX_14')
            trend_strength = "Weak"
            if adx is not None and not pd.isna(adx):
                adx = float(adx)
                if adx > 50:
                    trend_strength = "Very Strong"
                elif adx > 25:
                    trend_strength = "Strong"

            # Supertrend - Find direction column dynamically
            st_dir = None
            for key in row.keys():
                if isinstance(key, str) and 'SUPERT' in key and 'd' in key:
                    val = row[key]
                    if val is not None and not pd.isna(val):
                        st_dir = float(val)
                        break
            
            if st_dir == 1:
                signals.append("Supertrend Bullish")
                sentiment_score += 1.0
            elif st_dir == -1:
                signals.append("Supertrend Bearish")
                sentiment_score -= 1.0

            # Ichimoku Cloud
            span_a = row.get('ISA_9')
            span_b = row.get('ISB_26')
            if span_a is not None and span_b is not None:
                # Convert to scalar if Series, then check for NaN
                try:
                    if isinstance(span_a, pd.Series):
                        span_a = span_a.iloc[0] if len(span_a) > 0 else None
                    if isinstance(span_b, pd.Series):
                        span_b = span_b.iloc[0] if len(span_b) > 0 else None
                    
                    # Check if values are valid (not None and not NaN)
                    if span_a is not None and span_b is not None:
                        span_a_val = pd.to_numeric(span_a, errors='coerce')
                        span_b_val = pd.to_numeric(span_b, errors='coerce')
                        
                        if not pd.isna(span_a_val) and not pd.isna(span_b_val):
                            span_a = float(span_a_val)
                            span_b = float(span_b_val)
                            if close > span_a and close > span_b:
                                signals.append("Price above Ichimoku Cloud (Bullish)")
                                sentiment_score += 0.5
                            elif close < span_a and close < span_b:
                                signals.append("Price below Ichimoku Cloud (Bearish)")
                                sentiment_score -= 0.5
                except Exception as ichi_error:
                    logger.debug(f"Error processing Ichimoku for symbol: {ichi_error}")
                    pass

            # Final Signal Classification
            final_signal = "NEUTRAL"
            if sentiment_score >= 2.0:
                final_signal = "STRONG BUY"
            elif sentiment_score >= 0.5:
                final_signal = "BUY"
            elif sentiment_score <= -2.0:
                final_signal = "STRONG SELL"
            elif sentiment_score <= -0.5:
                final_signal = "SELL"

            # Prepare indicators dict (exclude OHLCV and timestamp)
            indicators = {}
            exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for k, v in row.items():
                if k not in exclude_cols:
                    try:
                        # Convert Series to scalar if needed
                        if isinstance(v, pd.Series):
                            v = v.iloc[0] if len(v) > 0 else None
                        
                        # Check for None or NaN
                        if v is None:
                            indicators[k] = None
                        elif isinstance(v, pd.Series):
                            # Still a Series after extraction attempt
                            indicators[k] = None
                        elif pd.isna(v) if not isinstance(v, (str, type(None))) else False:
                            indicators[k] = None
                        elif isinstance(v, (np.integer, np.floating)):
                            indicators[k] = float(v)
                        elif isinstance(v, (int, float)):
                            indicators[k] = float(v)
                        else:
                            indicators[k] = str(v)
                    except Exception:
                        indicators[k] = None

            # Get indicator ranges and zones
            indicator_ranges = self.get_indicator_ranges(row)
            
            return {
                'price': float(close),  # Price from OHLCV (may be slightly delayed)
                'rsi': float(rsi) if rsi is not None and not pd.isna(rsi) else None,
                'macd': float(row[macd_col]) if macd_col in row and not pd.isna(row[macd_col]) else None,
                'adx': float(adx) if adx is not None and not pd.isna(adx) else None,
                'adx_strength': trend_strength,
                'sentiment_score': round(float(sentiment_score), 2),
                'signals': signals,
                'final_signal': final_signal,
                'indicators': indicators,
                'indicator_ranges': indicator_ranges,  # New: Detailed ranges and zones
                'data_source': 'Binance (CCXT)'  # Indicate data source
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def get_market_data(self):
        """Fetch and analyze live market data for all symbols using CCXT"""
        results = []
        try:
            # Ensure markets are loaded first
            await self.load_markets()
            
            # Fetch all symbols concurrently for better performance
            logger.info(f"Fetching live data for {len(self.symbols)} symbols from Binance...")
            tasks = [self.fetch_ohlcv(symbol) for symbol in self.symbols]
            dfs = await asyncio.gather(*tasks, return_exceptions=True)

            # Process each symbol's data
            for i, df in enumerate(dfs):
                symbol = self.symbols[i]
                if isinstance(df, Exception):
                    logger.error(f"Failed to fetch {symbol}: {df}")
                    continue
                    
                if df is not None and not df.empty:
                    try:
                        # Calculate technical indicators
                        latest = self.calculate_indicators(df)
                        if latest is not None:
                            # Analyze and generate signals
                            analysis = self.analyze_sentiment_and_signal(latest)
                            if analysis:
                                analysis['symbol'] = symbol
                                
                                # Get live ticker for most recent price
                                ticker = await self.fetch_ticker(symbol)
                                if ticker:
                                    analysis['live_price'] = ticker.get('last')
                                    analysis['price_change_24h'] = ticker.get('change')
                                    analysis['volume_24h'] = ticker.get('volume')
                                
                                # Get order book data for order movements
                                orderbook = await self.fetch_orderbook(symbol)
                                if orderbook:
                                    analysis['orderbook'] = orderbook
                                
                                # Fetch news for this symbol
                                news = await self.fetch_crypto_news(symbol, limit=3)
                                if news:
                                    analysis['news'] = news
                                
                                # Add fundamental data
                                fundamental = self.get_fundamental_data(symbol)
                                analysis['fundamental'] = fundamental
                                
                                # Add timestamp of last update
                                analysis['last_update'] = pd.Timestamp.now().isoformat()
                                
                                results.append(analysis)
                    except Exception as calc_error:
                        logger.error(f"Error calculating/analyzing {symbol}: {calc_error}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
            
            logger.info(f"Successfully processed {len(results)} symbols")
                        
        except Exception as main_error:
            logger.error(f"Critical error in get_market_data: {main_error}")
            import traceback
            logger.error(traceback.format_exc())
        
        return results
    
    async def close(self):
        """Close exchange connection"""
        try:
            await self.exchange.close()
        except Exception as e:
            logger.error(f"Error closing exchange: {e}")
