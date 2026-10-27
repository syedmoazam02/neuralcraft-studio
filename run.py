"""NeuralCraft Studio application entrypoint."""
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from app.api import router

app = FastAPI(title="NeuralCraft Studio", version="1.0.0")
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/", response_class=HTMLResponse)
def serve_dashboard():
    dashboard = Path(__file__).resolve().parent / "app" / "templates" / "dashboard.html"
    if dashboard.exists():
        return HTMLResponse(content=dashboard.read_text(encoding="utf-8"))
    return FileResponse(dashboard, media_type="text/html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
