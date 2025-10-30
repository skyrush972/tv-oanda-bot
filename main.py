from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
def ping():
    return {"status": "ok"}

@app.post("/signal")
async def signal(req: Request):
    data = await req.json()
    print("signal:", data)
    return {"ok": True, "data": data}
