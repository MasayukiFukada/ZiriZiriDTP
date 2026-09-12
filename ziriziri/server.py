"""FastAPI Web Application and Printer Server for ZiriZiriDTP."""

import base64
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ziriziri.config import STATIC_DIR
from ziriziri.driver import PrinterDriver
from ziriziri.renderer import (
    render_todo_receipt,
    render_free_text,
    render_image_dither,
    render_test_chart,
    pil_to_chunks,
    image_to_base64_png,
)

app = FastAPI(title="ZiriZiriDTP Web Server")

# Serve static directory
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

driver = PrinterDriver()


# ─────────────────────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────────────────────

class TodoItem(BaseModel):
    text: str
    checked: bool = False


class TodoRequest(BaseModel):
    title: str = "TODO LIST"
    items: List[TodoItem]
    footer: Optional[str] = "ZiriZiriDTP * SWS-PT1"
    density: int = 3
    feed: int = 40


class TextRequest(BaseModel):
    text: str
    font_size: int = 18
    align: str = "left"  # "left", "center", "right"
    is_bold: bool = False
    density: int = 3
    feed: int = 40


class TestChartRequest(BaseModel):
    density: int = 3
    feed: int = 40


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve SPA front-end."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"status": "Frontend not ready yet."})
    return FileResponse(index_file)


@app.get("/api/status")
async def get_status():
    """Fetch real-time printer status (battery, connection)."""
    status = await driver.get_status()
    return status


@app.post("/api/preview/todo")
async def preview_todo(req: TodoRequest):
    """Generate preview image for TODO list."""
    img = render_todo_receipt(
        title=req.title,
        items=[itm.model_dump() for itm in req.items],
        footer_text=req.footer,
    )
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/todo")
async def print_todo(req: TodoRequest):
    """Render and print TODO list."""
    img = render_todo_receipt(
        title=req.title,
        items=[itm.model_dump() for itm in req.items],
        footer_text=req.footer,
    )
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=req.density, feed_after=req.feed)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to print. Ensure printer is turned on.")
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}


@app.post("/api/preview/text")
async def preview_text(req: TextRequest):
    """Generate preview image for free text."""
    img = render_free_text(
        text=req.text,
        font_size=req.font_size,
        align=req.align,
        is_bold=req.is_bold,
    )
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/text")
async def print_text(req: TextRequest):
    """Render and print free text."""
    img = render_free_text(
        text=req.text,
        font_size=req.font_size,
        align=req.align,
        is_bold=req.is_bold,
    )
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=req.density, feed_after=req.feed)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to print. Ensure printer is turned on.")
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}


@app.post("/api/preview/image")
async def preview_image(
    file: UploadFile = File(...),
    dither: bool = Form(True),
    contrast: float = Form(1.0),
):
    """Generate preview image for uploaded photo."""
    content = await file.read()
    img = render_image_dither(content, dither=dither, contrast=contrast)
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/image")
async def print_image_upload(
    file: UploadFile = File(...),
    dither: bool = Form(True),
    contrast: float = Form(1.0),
    density: int = Form(3),
    feed: int = Form(40),
):
    """Render and print uploaded photo."""
    content = await file.read()
    img = render_image_dither(content, dither=dither, contrast=contrast)
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=density, feed_after=feed)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to print image.")
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}


@app.post("/api/preview/test")
async def preview_test_chart():
    """Generate preview image for diagnostic test chart."""
    img = render_test_chart()
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/test")
async def print_test_chart(req: TestChartRequest):
    """Print diagnostic test chart."""
    img = render_test_chart()
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=req.density, feed_after=req.feed)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to print test chart.")
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}

