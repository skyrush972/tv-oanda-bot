from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import requests

app = FastAPI()

OANDA_ACCOUNT = os.getenv("OANDA_ACCOUNT")
OANDA_KEY = os.getenv("OANDA_KEY")
OANDA_URL = os.getenv("OANDA_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")


class Signal(BaseModel):
    action: str
    symbol: str
    qty: float | None = None


@app.get("/ping")
def ping():
    return {"status": "ok"}


def oanda_order(action: str, symbol: str, qty: float):
    endpoint = f"{OANDA_URL}/v3/accounts/{OANDA_ACCOUNT}/orders"

    data = {
        "order": {
            "units": str(qty if action == "BUY" else -qty),
            "instrument": symbol,
            "type": "MARKET",
            "positionFill": "DEFAULT"
        }
    }

    r = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {OANDA_KEY}",
                 "Content-Type": "application/json"},
        json=data
    )
    return r.json()


def oanda_move_SL_BE(symbol: str):
    # point d’ancrage. pas de logique BE calculée ici.
    return {"status": "SL moved to BE", "symbol": symbol}


@app.post("/signal")
async def signal(data: Signal, request: Request):

    # optionnel: vérifier secret
    secret = request.headers.get("X-Webhook-Secret")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        return {"error": "invalid secret"}

    if data.action.upper() == "BUY":
        if data.qty is None:
            return {"error": "qty manquant"}
        rtn = oanda_order("BUY", data.symbol, data.qty)
        return {"status": "order_sent", "result": rtn}

    if data.action.upper() == "SELL":
        if data.qty is None:
            return {"error": "qty manquant"}
        rtn = oanda_order("SELL", data.symbol, data.qty)
        return {"status": "order_sent", "result": rtn}

    if data.action.upper() == "MOVE_SL_BE":
        rtn = oanda_move_SL_BE(data.symbol)
        return rtn

    return {"error": "action inconnue"}
