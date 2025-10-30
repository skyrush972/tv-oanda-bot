import os
import requests
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

OANDA_KEY     = os.environ["OANDA_KEY"]
ACCOUNT_ID    = os.environ["OANDA_ACCOUNT"]
OANDA_URL     = os.environ["OANDA_URL"]
WEBHOOK_SECRET= os.environ["WEBHOOK_SECRET"]

HEADERS = {
    "Authorization": f"Bearer {OANDA_KEY}",
    "Content-Type": "application/json"
}

def sanitize_symbol(tv_symbol: str) -> str:
    """OANDA format helper  ex: OANDA:GBPUSD → GBP_USD"""
    s = tv_symbol.split(":")[-1].upper()
    if len(s) == 6:
        return f"{s[0:3]}_{s[3:6]}"
    return s.replace("/", "_")

def open_market(instrument, units, sl=None, tp=None):
    url = f"{OANDA_URL}/v3/accounts/{ACCOUNT_ID}/orders"

    order = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK"
        }
    }

    if sl:
        order["order"]["stopLossOnFill"] = {"price": f"{sl:.5f}"}
    if tp:
        order["order"]["takeProfitOnFill"] = {"price": f"{tp:.5f}"}

    r = requests.post(url, json=order, headers=HEADERS)
    return r.json()

def get_open_trades(instrument):
    url = f"{OANDA_URL}/v3/accounts/{ACCOUNT_ID}/openTrades"
    r = requests.get(url, headers=HEADERS).json()
    trades = r.get("trades", [])
    return [t for t in trades if t["instrument"] == instrument]

def replace_sl(trade_id, price):
    url = f"{OANDA_URL}/v3/accounts/{ACCOUNT_ID}/orders"
    payload = {
        "order": {
            "type": "STOP_LOSS",
            "tradeID": trade_id,
            "timeInForce": "GTC",
            "price": f"{price:.5f}"
        }
    }
    return requests.post(url, json=payload, headers=HEADERS).json()

@app.get("/")
def ping():
    return {"status": "ok"}

@app.post("/signal")
async def signal(request: Request):
    sig = request.headers.get("X-Webhook-Secret", "")
    if sig != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Bad Secret")

    data = await request.json()

    typ   = data.get("type")       # ENTRY | BE
    side  = data.get("side")       # buy | sell
    sym   = data.get("symbol")     # ex: OANDA:GBPUSD
    sl    = data.get("sl")
    tp    = data.get("tp")
    units = data.get("units")

    instrument = sanitize_symbol(sym)

    # ========== ENTRY ==========
    if typ == "ENTRY":
        if side not in ("buy", "sell"):
            return {"error": "side missing"}

        u = abs(int(units)) if side == "buy" else -abs(int(units))
        res = open_market(instrument, u, sl, tp)
        return {"action": "entry", "result": res}

    # ========== BE ==========
    if typ == "BE":
        trades = get_open_trades(instrument)
        if not trades:
            return {"action": "be", "result": "no open trade"}

        # prend le plus récent
        last = sorted(trades, key=lambda t: t["openTime"])[-1]
        entry_price = float(last["price"])

        res = replace_sl(last["id"], entry_price)
        return {"action": "be", "result": res}

    return {"error": "invalid type"}
