"""Image and receipt rendering engine for thermal printing."""

import base64
from io import BytesIO
from itertools import islice
from typing import List, Optional
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageOps

from ziriziri.config import PRINTER_WIDTH, DEFAULT_FONT_PATH, FALLBACK_FONT_PATH


def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Load system Japanese font with fallback."""
    for path in [DEFAULT_FONT_PATH, FALLBACK_FONT_PATH]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def pil_to_chunks(img_1bit: Image.Image) -> List[bytes]:
    """Convert a 1-bit PIL image of width 384 into 96-byte FunnyPrint chunks.

    Each chunk contains 2 raster lines (48 bytes + 48 bytes).
    Bits are inverted so that black pixels (0 in PIL mode '1') become 1 for thermal heads.
    """
    raw = img_1bit.tobytes()
    bpl = PRINTER_WIDTH // 8  # 48 bytes per line
    lines = [
        bytes([b ^ 0xFF for b in raw[i : i + bpl]])
        for i in range(0, len(raw), bpl)
    ]
    result = []
    it = iter(lines)
    while pair := tuple(islice(it, 2)):
        combined = bytearray(96)
        combined[: len(pair[0])] = pair[0]
        if len(pair) == 2:
            combined[48 : 48 + len(pair[1])] = pair[1]
        result.append(bytes(combined))
    return result


def image_to_base64_png(img: Image.Image) -> str:
    """Encode PIL image as base64 PNG data URL."""
    buf = BytesIO()
    # Convert mode 1 to RGB for clean web preview rendering
    rgb_img = img.convert("RGB")
    rgb_img.save(buf, format="PNG")
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def render_todo_receipt(
    title: str = "TODO LIST",
    items: Optional[List[dict]] = None,
    footer_text: Optional[str] = None,
) -> Image.Image:
    """Render receipt style TODO / Shopping list."""
    items = items or []
    w = PRINTER_WIDTH
    font_title = get_font(26, bold=True)
    font_date = get_font(13)
    font_item = get_font(16)
    font_sub = get_font(12)

    # Estimate height
    line_h = 32
    header_h = 80
    footer_h = 50
    total_h = header_h + max(1, len(items)) * line_h + footer_h
    if total_h % 2 != 0:
        total_h += 1

    img = Image.new("1", (w, total_h), 1)
    draw = ImageDraw.Draw(img)

    # Header decorative borders
    draw.rectangle([(0, 0), (w - 1, 4)], fill=0)
    draw.rectangle([(0, 7), (w - 1, 9)], fill=0)

    # Title
    draw.text((w // 2, 28), title, font=font_title, fill=0, anchor="mm")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((w // 2, 52), now_str, font=font_date, fill=0, anchor="mm")

    # Separator dotted line
    for x in range(12, w - 12, 6):
        draw.line([(x, 68), (x + 3, 68)], fill=0, width=1)

    # Items
    y = 80
    for itm in items:
        checked = itm.get("checked", False)
        text = itm.get("text", "")

        # Checkbox square (16x16)
        bx, by = 20, y + 4
        draw.rectangle([(bx, by), (bx + 16, by + 16)], fill=1, outline=0, width=2)
        if checked:
            # Check mark inside
            draw.line([(bx + 3, by + 8), (bx + 7, by + 13)], fill=0, width=2)
            draw.line([(bx + 7, by + 13), (bx + 14, by + 3)], fill=0, width=2)
            # Strikethrough for checked item
            draw.text((45, y + 2), text, font=font_item, fill=0)
            text_bbox = draw.textbbox((45, y + 2), text, font=font_item)
            strike_y = (text_bbox[1] + text_bbox[3]) // 2
            draw.line([(42, strike_y), (text_bbox[2] + 4, strike_y)], fill=0, width=1)
        else:
            draw.text((45, y + 2), text, font=font_item, fill=0)

        y += line_h

    # Footer separator
    draw.line([(12, y + 6), (w - 12, y + 6)], fill=0, width=1)

    # Footer
    f_text = footer_text or "ZiriZiriDTP * SWS-PT1"
    draw.text((w // 2, y + 22), f_text, font=font_sub, fill=0, anchor="mm")

    # Bottom border
    draw.rectangle([(0, total_h - 4), (w - 1, total_h - 1)], fill=0)

    return img


def render_free_text(
    text: str,
    font_size: int = 18,
    align: str = "left",
    is_bold: bool = False,
    show_border: bool = True,
) -> Image.Image:
    """Render arbitrary multiline text with formatting."""
    w = PRINTER_WIDTH
    font = get_font(font_size, bold=is_bold)
    lines = text.split("\n")
    if not lines:
        lines = [""]

    line_spacing = int(font_size * 0.4)
    line_h = font_size + line_spacing
    pad = 20 if show_border else 10
    total_h = pad * 2 + len(lines) * line_h + 10
    if total_h % 2 != 0:
        total_h += 1

    img = Image.new("1", (w, total_h), 1)
    draw = ImageDraw.Draw(img)

    if show_border:
        draw.rectangle([(0, 0), (w - 1, 3)], fill=0)

    y = pad
    for line in lines:
        if align == "center":
            draw.text((w // 2, y), line, font=font, fill=0, anchor="mt")
        elif align == "right":
            draw.text((w - pad, y), line, font=font, fill=0, anchor="ra")
        else:
            draw.text((pad, y), line, font=font, fill=0)
        y += line_h

    if show_border:
        draw.rectangle([(0, total_h - 3), (w - 1, total_h - 1)], fill=0)

    return img


def render_image_dither(
    image_bytes: bytes,
    dither: bool = True,
    contrast: float = 1.0,
) -> Image.Image:
    """Resize arbitrary image to 384 width and apply Floyd-Steinberg dithering."""
    with Image.open(BytesIO(image_bytes)) as src:
        # Convert to grayscale
        gray = src.convert("L")

        # Proportional resize to 384 px width
        w_orig, h_orig = gray.size
        new_h = max(2, int(h_orig * PRINTER_WIDTH / w_orig))
        if new_h % 2 != 0:
            new_h += 1
        resized = gray.resize((PRINTER_WIDTH, new_h), Image.Resampling.LANCZOS)

        # Contrast adjustment
        if contrast != 1.0:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(resized)
            resized = enhancer.enhance(contrast)

        # Dithering (Floyd-Steinberg vs Threshold)
        if dither:
            dithered = resized.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
        else:
            dithered = resized.point(lambda p: 255 if p > 128 else 0, mode="1")

        return dithered


def render_test_chart() -> Image.Image:
    """Generate diagnostic print test chart."""
    w = PRINTER_WIDTH
    h = 320
    img = Image.new("1", (w, h), 1)
    draw = ImageDraw.Draw(img)

    font_title = get_font(20, bold=True)
    font_body = get_font(14)
    font_small = get_font(11)

    # 1. Header
    draw.rectangle([(0, 0), (w - 1, 4)], fill=0)
    draw.text((w // 2, 18), "=== PRINTER TEST CHART ===", font=font_title, fill=0, anchor="mm")
    draw.text((w // 2, 38), "SWS-PT1 (203 DPI / 384 dots)", font=font_small, fill=0, anchor="mm")
    draw.line([(10, 50), (w - 10, 50)], fill=0)

    # 2. Font Size Ladder
    draw.text((15, 60), "8pt: あいうえお ABCDEFG 012345", font=get_font(12), fill=0)
    draw.text((15, 78), "12pt: あいうえお ABCDEFG 012345", font=get_font(16), fill=0)
    draw.text((15, 100), "16pt: かんたん印刷テスト", font=get_font(20), fill=0)
    draw.text((15, 126), "20pt: ZiriZiri DTP", font=get_font(24, bold=True), fill=0)

    # 3. Density Gradient / Dithering Steps
    draw.line([(10, 160), (w - 10, 160)], fill=0)
    draw.text((15, 168), "Dithering Grayscale Gradient:", font=font_small, fill=0)

    # Gradient bar
    steps = 10
    step_w = (w - 30) // steps
    for s in range(steps):
        gray_val = int(255 * s / (steps - 1))
        # Draw dotted pattern according to gray_val
        bx = 15 + s * step_w
        by = 185
        draw.rectangle([(bx, by), (bx + step_w - 2, by + 30)], outline=0)
        # Fill with dither simulation
        for py in range(by + 2, by + 28, 2):
            for px in range(bx + 2, bx + step_w - 4, 2):
                if (px + py) % (steps + 1 - s) == 0:
                    draw.point((px, py), fill=0)

    # 4. Dot alignment & Ruler
    draw.text((15, 230), "Resolution Ruler (10px / 50px ticks):", font=font_small, fill=0)
    draw.line([(15, 255), (w - 15, 255)], fill=0, width=2)
    for x in range(15, w - 15, 10):
        tick_h = 10 if (x - 15) % 50 == 0 else 4
        draw.line([(x, 255), (x, 255 + tick_h)], fill=0, width=1)
        if (x - 15) % 50 == 0 and (x - 15) > 0:
            draw.text((x, 268), str(x - 15), font=font_small, fill=0, anchor="mt")

    # 5. Bottom border
    draw.rectangle([(0, h - 6), (w - 1, h - 1)], fill=0)
    return img
