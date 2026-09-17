import asyncio
import base64
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from ziriziri.config import STATIC_DIR
from ziriziri.driver import PrinterDriver
from ziriziri.renderer import (
    render_todo_receipt,
    render_route_sheet,
    render_free_text,
    render_image_dither,
    render_test_chart,
    append_cut_line,
    pil_to_chunks,
    image_to_base64_png,
)

app = FastAPI(title="ZiriZiriDTP Web Server")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"サーバー内部エラーが発生しました: {str(exc)}"}
    )

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
    qr_type: Optional[str] = None  # "url", "map", "memo", None
    qr_data: Optional[str] = None


class TodoRequest(BaseModel):
    title: str = "TODO LIST"
    items: List[TodoItem]
    footer: Optional[str] = "ZiriZiriDTP * SWS-PT1"
    show_datetime: bool = True
    datetime_position: str = "header"  # "header" or "footer"
    show_cut_line: bool = True
    density: int = 1
    feed: int = 40


class RouteItem(BaseModel):
    name: str
    location: Optional[str] = None
    note: Optional[str] = None
    checked: bool = False
    action: str = "navigate"  # "navigate" or "search"


class RouteRequest(BaseModel):
    title: str = "🚗 ドライブルート"
    items: List[RouteItem]
    travel_mode: str = "driving"  # "driving", "bicycling", "walking", "transit"
    footer: Optional[str] = "ZiriZiriDTP * Safe Trip!"
    show_datetime: bool = True
    datetime_position: str = "header"  # "header" or "footer"
    show_cut_line: bool = True
    density: int = 1
    feed: int = 40


class TextRequest(BaseModel):
    text: str
    font_size: int = 18
    align: str = "left"  # "left", "center", "right"
    is_bold: bool = False
    show_datetime: bool = True
    datetime_position: str = "header"  # "header" or "footer"
    show_cut_line: bool = True
    density: int = 1
    feed: int = 40


class TestChartRequest(BaseModel):
    density: int = 1
    feed: int = 40
    show_datetime: bool = True
    datetime_position: str = "footer"
    show_cut_line: bool = True


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
        show_datetime=req.show_datetime,
        datetime_position=req.datetime_position,
    )
    if req.show_cut_line:
        img = append_cut_line(img)
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/todo")
async def print_todo(req: TodoRequest):
    """Render and print TODO list."""
    img = render_todo_receipt(
        title=req.title,
        items=[itm.model_dump() for itm in req.items],
        footer_text=req.footer,
        show_datetime=req.show_datetime,
        datetime_position=req.datetime_position,
    )
    if req.show_cut_line:
        img = append_cut_line(img)
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=req.density, feed_after=req.feed)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="プリンタと通信できませんでした。プリンタの電源が入っているか確認してください。"
        )
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}


@app.post("/api/preview/route")
async def preview_route(req: RouteRequest):
    """Generate preview image for travel/drive route sheet."""
    img = render_route_sheet(
        title=req.title,
        items=[itm.model_dump() for itm in req.items],
        travel_mode=req.travel_mode,
        footer_text=req.footer,
        show_datetime=req.show_datetime,
        datetime_position=req.datetime_position,
        show_cut_line=req.show_cut_line,
    )
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/route")
async def print_route(req: RouteRequest):
    """Render and print travel/drive route sheet with 2-spot cooling pause pacing."""
    img = render_route_sheet(
        title=req.title,
        items=[itm.model_dump() for itm in req.items],
        travel_mode=req.travel_mode,
        footer_text=req.footer,
        show_datetime=req.show_datetime,
        datetime_position=req.datetime_position,
        show_cut_line=req.show_cut_line,
    )
    chunks = pil_to_chunks(img)
    pause_chunks = img.info.get("pause_chunks", [])

    async def event_generator():
        event_queue = asyncio.Queue()

        def on_prog(cur, total):
            pct = int(cur / total * 100)
            event_queue.put_nowait({
                "type": "progress",
                "cur": cur,
                "total": total,
                "percent": pct,
                "message": f"🖨️ 印刷中… ({pct}%)",
            })

        def on_pause(p_info, duration):
            finished = p_info.get("finished_spots", "")
            next_sp = p_info.get("next_spots", "")
            msg = f"☕ プリンタ冷却・休憩中 ({duration:.0f}秒)…"
            if finished:
                msg = f"☕ スポット [{finished}] 完了！冷却休憩中…"
            event_queue.put_nowait({
                "type": "pause",
                "duration": duration,
                "message": msg,
            })

        async def run_print():
            try:
                ok = await driver.print_chunks(
                    chunks,
                    density=req.density,
                    feed_after=req.feed,
                    pause_chunks=pause_chunks,
                    pause_duration=3.5,
                    on_progress=on_prog,
                    on_pause=on_pause,
                )
                if ok:
                    event_queue.put_nowait({"type": "done", "status": "ok", "battery": driver.battery})
                else:
                    event_queue.put_nowait({
                        "type": "done",
                        "status": "error",
                        "detail": "プリンタと通信できませんでした。プリンタの電源が入っているか確認してください。",
                    })
            except Exception as e:
                event_queue.put_nowait({"type": "done", "status": "error", "detail": str(e)})

        task = asyncio.create_task(run_print())
        event_queue.put_nowait({
            "type": "progress",
            "cur": 0,
            "total": len(chunks),
            "percent": 0,
            "message": "🖨️ プリンタへ接続・送信中…",
        })

        while not task.done() or not event_queue.empty():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.2)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                continue

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/preview/text")
async def preview_text(req: TextRequest):
    """Generate preview image for free text."""
    img = render_free_text(
        text=req.text,
        font_size=req.font_size,
        align=req.align,
        is_bold=req.is_bold,
        show_datetime=req.show_datetime,
        datetime_position=req.datetime_position,
    )
    if req.show_cut_line:
        img = append_cut_line(img)
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/text")
async def print_text(req: TextRequest):
    """Render and print free text."""
    img = render_free_text(
        text=req.text,
        font_size=req.font_size,
        align=req.align,
        is_bold=req.is_bold,
        show_datetime=req.show_datetime,
        datetime_position=req.datetime_position,
    )
    if req.show_cut_line:
        img = append_cut_line(img)
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=req.density, feed_after=req.feed)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="プリンタと通信できませんでした。プリンタの電源が入っているか確認してください。"
        )
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}


@app.post("/api/preview/image")
async def preview_image(
    file: UploadFile = File(...),
    dither: bool = Form(True),
    contrast: float = Form(1.0),
    show_datetime: bool = Form(True),
    datetime_position: str = Form("footer"),
    show_cut_line: bool = Form(True),
):
    """Generate preview image for uploaded photo."""
    content = await file.read()
    img = render_image_dither(
        content,
        dither=dither,
        contrast=contrast,
        show_datetime=show_datetime,
        datetime_position=datetime_position,
    )
    if show_cut_line:
        img = append_cut_line(img)
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/image")
async def print_image_upload(
    file: UploadFile = File(...),
    dither: bool = Form(True),
    contrast: float = Form(1.0),
    show_datetime: bool = Form(True),
    datetime_position: str = Form("footer"),
    show_cut_line: bool = Form(True),
    density: int = Form(1),
    feed: int = Form(40),
):
    """Render and print uploaded photo."""
    content = await file.read()
    img = render_image_dither(
        content,
        dither=dither,
        contrast=contrast,
        show_datetime=show_datetime,
        datetime_position=datetime_position,
    )
    if show_cut_line:
        img = append_cut_line(img)
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=density, feed_after=feed)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="プリンタと通信できませんでした。プリンタの電源が入っているか確認してください。"
        )
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}



@app.post("/api/preview/test")
async def preview_test_chart(req: Optional[TestChartRequest] = None):
    """Generate preview image for diagnostic test chart."""
    show_datetime = req.show_datetime if req else True
    datetime_position = req.datetime_position if req else "footer"
    show_cut_line = req.show_cut_line if req else True
    img = render_test_chart(show_datetime=show_datetime, datetime_position=datetime_position)
    if show_cut_line:
        img = append_cut_line(img)
    return {"preview": image_to_base64_png(img), "height": img.height}


@app.post("/api/print/test")
async def print_test_chart(req: TestChartRequest):
    """Print diagnostic test chart."""
    img = render_test_chart(
        show_datetime=req.show_datetime,
        datetime_position=req.datetime_position,
    )
    if req.show_cut_line:
        img = append_cut_line(img)
    chunks = pil_to_chunks(img)
    success = await driver.print_chunks(chunks, density=req.density, feed_after=req.feed)
    if not success:
        raise HTTPException(
            status_code=503,
            detail="プリンタと通信できませんでした。プリンタの電源が入っているか確認してください。"
        )
    return {"status": "ok", "chunks": len(chunks), "battery": driver.battery}

