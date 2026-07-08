from fastapi import FastAPI

app = FastAPI(title="SFSIS API")


@app.get("/")
def read_root():
    return {"status": "ok"}
