"""
Retirement-Right v2 — FastAPI Application
Single endpoint: POST /generate
Takes v2 client JSON → runs engine → returns PDF binary
"""
import json
import io
import traceback
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.orchestrator import run_projection
from pdf.generator import generate_pdf

app = FastAPI(
    title="Retirement-Right v2 API",
    description="Retirement income projection engine + PDF generator",
    version="2.0.0",
)

# Allow requests from Lovable, localhost dev, and any future domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClientPayload(BaseModel):
    model_config = {"extra": "allow"}
    schema_version: str = "2.0"


@app.get("/")
def root():
    return {
        "service": "Retirement-Right v2 API",
        "version": "2.0.0",
        "status": "online",
        "endpoints": {
            "POST /generate": "Takes v2 client JSON, returns PDF",
            "POST /projection": "Takes v2 client JSON, returns projection data as JSON",
            "GET  /health": "Health check",
            "GET  /validate": "Schema validation only",
        }
    }


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/generate")
async def generate(request: Request):
    """
    Main endpoint.
    Accepts: application/json — v2 client JSON
    Returns: application/pdf — generated report
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Validate schema version
    if body.get("schema_version") != "2.0":
        raise HTTPException(
            status_code=400,
            detail=f"Expected schema_version '2.0', got '{body.get('schema_version')}'. "
                   "Please migrate your client data to v2 format."
        )

    # Run projection engine
    try:
        projection = run_projection(body)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Projection engine error: {str(e)}\n{traceback.format_exc()}"
        )

    # Generate PDF
    try:
        pdf_bytes = generate_pdf(body, projection)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation error: {str(e)}\n{traceback.format_exc()}"
        )

    # Build filename from client name and date
    client = body.get("client", {})
    name   = f"{client.get('last_name','client')}".lower().replace(" ","_")
    date   = datetime.utcnow().strftime("%Y%m%d")
    filename = f"retirement_blueprint_{name}_{date}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/projection")
async def projection_json(request: Request):
    """
    Returns the full projection as JSON (no PDF).
    Useful for the React frontend to display data before generating PDF.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if body.get("schema_version") != "2.0":
        raise HTTPException(status_code=400, detail="Expected schema_version '2.0'")

    try:
        projection = run_projection(body)
        return JSONResponse(content=projection)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Engine error: {str(e)}"
        )


@app.post("/validate")
async def validate_schema(request: Request):
    """
    Validates a client JSON against the v2 schema.
    Returns field-level errors if invalid.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        import jsonschema
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema_v2.json")
        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(instance=body, schema=schema)
        return {"valid": True, "errors": []}
    except jsonschema.ValidationError as e:
        return {"valid": False, "errors": [{"path": list(e.path), "message": e.message}]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
