from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.scanner import CryptoScanner
import uvicorn
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crypto Technical Scanner",
    description="Real-time cryptocurrency technical analysis scanner with 15+ indicators",
    version="1.0.0"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scanner
scanner = CryptoScanner()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def read_root():
    """Serve the main HTML page"""
    return FileResponse('app/static/index.html')

@app.get("/api/scan")
async def scan_market():
    """Fetch and analyze market data for all configured symbols"""
    try:
        data = await scanner.get_market_data()
        return {"data": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Error in scan_market endpoint: {e}")
        return {"data": [], "error": str(e), "count": 0}

@app.get("/api/ticker/{symbol}")
async def get_ticker(symbol: str):
    """Get live ticker data for a specific symbol"""
    try:
        ticker = await scanner.fetch_ticker(symbol)
        if ticker:
            return {"success": True, "data": ticker}
        return {"success": False, "error": "Ticker not found"}
    except Exception as e:
        logger.error(f"Error fetching ticker for {symbol}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/orderbook/{symbol}")
async def get_orderbook(symbol: str):
    """Get order book data for a specific symbol"""
    try:
        orderbook = await scanner.fetch_orderbook(symbol)
        if orderbook:
            return {"success": True, "data": orderbook}
        return {"success": False, "error": "Orderbook not found"}
    except Exception as e:
        logger.error(f"Error fetching orderbook for {symbol}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/news/{symbol}")
async def get_news(symbol: str):
    """Get news for a specific symbol"""
    try:
        news = await scanner.fetch_crypto_news(symbol, limit=10)
        return {"success": True, "data": news}
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "crypto-scanner",
        "exchange": "Binance (via CCXT)",
        "data_source": "Live"
    }

@app.on_event("startup")
async def startup_event():
    """Initialize on application startup"""
    try:
        await scanner.load_markets()
        logger.info("Scanner initialized and markets loaded")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    await scanner.close()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
