from fastapi import FastAPI

app = FastAPI(title="NAZON")

@app.get("/")
def home():
    return {"system": "NAZON", "status": "online"}

@app.get("/health")
def health():
    return {"ok": True}
