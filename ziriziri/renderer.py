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


def append_cut_line(img: Image.Image) -> Image.Image:
    """Append a dashed scissors cut line to the bottom of the image for clean manual cutting."""
    w = PRINTER_WIDTH
    cut_h = 32
    total_h = img.height + cut_h
    if total_h % 2 != 0:
        total_h += 1

    new_img = Image.new("1", (w, total_h), 1)
    new_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(new_img)
    y = img.height + 16

    font_cut = get_font(11)
    font_scissor = get_font(13)

    # Left scissors
    draw.text((12, y), "✂", font=font_scissor, fill=0, anchor="lm")

    # Center text "キリトリ"
    center_text = "キリトリ"
    draw.text((w // 2, y), center_text, font=font_cut, fill=0, anchor="mm")
    bbox = draw.textbbox((w // 2, y), center_text, font=font_cut, anchor="mm")

    # Dashed lines
    dash_len = 6
    gap = 4

    # Left dashes: from 28 to bbox[0] - 6
    for px in range(28, max(28, bbox[0] - 6), dash_len + gap):
        draw.line([(px, y), (min(px + dash_len, bbox[0] - 6), y)], fill=0, width=1)

    # Right dashes: from bbox[2] + 6 to w - 28
    for px in range(bbox[2] + 6, max(bbox[2] + 6, w - 28), dash_len + gap):
        draw.line([(px, y), (min(px + dash_len, w - 28), y)], fill=0, width=1)

    # Right scissors
    draw.text((w - 12, y), "✂", font=font_scissor, fill=0, anchor="rm")

    return new_img


def render_todo_receipt(
    title: str = "TODO LIST",
    items: Optional[List[dict]] = None,
    footer_text: Optional[str] = None,
    show_datetime: bool = True,
    datetime_position: str = "header",
) -> Image.Image:
    """Render receipt style TODO / Shopping list with optional timestamp."""
    items = items or []
    w = PRINTER_WIDTH
    font_title = get_font(26, bold=True)
    font_date = get_font(13)
    font_item = get_font(16)
    font_sub = get_font(12)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Estimate height
    line_h = 32
    header_h = 80 if (show_datetime and datetime_position == "header") else 60
    footer_h = 60 if (show_datetime and datetime_position == "footer") else 46
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
    
    sep_y = 48
    if show_datetime and datetime_position == "header":
        draw.text((w // 2, 50), now_str, font=font_date, fill=0, anchor="mm")
        sep_y = 66

    # Separator dotted line
    for x in range(12, w - 12, 6):
        draw.line([(x, sep_y), (x + 3, sep_y)], fill=0, width=1)

    # Items
    y = sep_y + 12
    for itm in items:
        checked = itm.get("checked", False)
        text = itm.get("text", "")

        # Checkbox square (16x16)
        bx, by = 20, y + 4
        draw.rectangle([(bx, by), (bx + 16, by + 16)], fill=1, outline=0, width=2)
        if checked:
            draw.line([(bx + 3, by + 8), (bx + 7, by + 13)], fill=0, width=2)
            draw.line([(bx + 7, by + 13), (bx + 14, by + 3)], fill=0, width=2)
            draw.text((45, y + 2), text, font=font_item, fill=0)
            text_bbox = draw.textbbox((45, y + 2), text, font=font_item)
            strike_y = (text_bbox[1] + text_bbox[3]) // 2
            draw.line([(42, strike_y), (text_bbox[2] + 4, strike_y)], fill=0, width=1)
        else:
            draw.text((45, y + 2), text, font=font_item, fill=0)

        y += line_h

    # Footer separator
    draw.line([(12, y + 6), (w - 12, y + 6)], fill=0, width=1)

    # Footer content
    fy = y + 20
    if show_datetime and datetime_position == "footer":
        draw.text((w // 2, fy), now_str, font=font_date, fill=0, anchor="mm")
        fy += 18

    f_text = footer_text or "ZiriZiriDTP * SWS-PT1"
    draw.text((w // 2, fy), f_text, font=font_sub, fill=0, anchor="mm")

    # Bottom border
    draw.rectangle([(0, total_h - 4), (w - 1, total_h - 1)], fill=0)

    return img


def render_free_text(
    text: str,
    font_size: int = 18,
    align: str = "left",
    is_bold: bool = False,
    show_border: bool = True,
    show_datetime: bool = True,
    datetime_position: str = "header",
) -> Image.Image:
    """Render arbitrary multiline text with optional timestamp."""
    w = PRINTER_WIDTH
    font = get_font(font_size, bold=is_bold)
    font_date = get_font(12)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = text.split("\n")
    if not lines:
        lines = [""]

    line_spacing = int(font_size * 0.4)
    line_h = font_size + line_spacing
    pad = 20 if show_border else 10
    
    date_h = 24 if show_datetime else 0
    total_h = pad * 2 + len(lines) * line_h + date_h + 10
    if total_h % 2 != 0:
        total_h += 1

    img = Image.new("1", (w, total_h), 1)
    draw = ImageDraw.Draw(img)

    if show_border:
        draw.rectangle([(0, 0), (w - 1, 3)], fill=0)

    y = pad

    # Header timestamp
    if show_datetime and datetime_position == "header":
        draw.text((w - pad, y), now_str, font=font_date, fill=0, anchor="ra")
        y += 20
        draw.line([(pad, y), (w - pad, y)], fill=0, width=1)
        y += 10

    for line in lines:
        if align == "center":
            draw.text((w // 2, y), line, font=font, fill=0, anchor="mt")
        elif align == "right":
            draw.text((w - pad, y), line, font=font, fill=0, anchor="ra")
        else:
            draw.text((pad, y), line, font=font, fill=0)
        y += line_h

    # Footer timestamp
    if show_datetime and datetime_position == "footer":
        y += 6
        draw.line([(pad, y), (w - pad, y)], fill=0, width=1)
        y += 6
        draw.text((w - pad, y), now_str, font=font_date, fill=0, anchor="ra")

    if show_border:
        draw.rectangle([(0, total_h - 3), (w - 1, total_h - 1)], fill=0)

    return img


def render_image_dither(
    image_bytes: bytes,
    dither: bool = True,
    contrast: float = 1.0,
    show_datetime: bool = True,
    datetime_position: str = "footer",
) -> Image.Image:
    """Resize image to 384px, apply dithering, and optionally add timestamp caption."""
    with Image.open(BytesIO(image_bytes)) as src:
        gray = src.convert("L")

        w_orig, h_orig = gray.size
        new_h = max(2, int(h_orig * PRINTER_WIDTH / w_orig))
        resized = gray.resize((PRINTER_WIDTH, new_h), Image.Resampling.LANCZOS)

        if contrast != 1.0:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(resized)
            resized = enhancer.enhance(contrast)

        if dither:
            dithered = resized.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
        else:
            dithered = resized.point(lambda p: 255 if p > 128 else 0, mode="1")

        if not show_datetime:
            if dithered.height % 2 != 0:
                dithered = dithered.crop((0, 0, PRINTER_WIDTH, dithered.height - 1))
            return dithered

        # Add timestamp frame / caption
        caption_h = 28
        total_h = dithered.height + caption_h
        if total_h % 2 != 0:
            total_h += 1

        final_img = Image.new("1", (PRINTER_WIDTH, total_h), 1)
        draw = ImageDraw.Draw(final_img)
        font_date = get_font(12)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        if datetime_position == "header":
            draw.text((PRINTER_WIDTH // 2, 12), f"PRINTED: {now_str}", font=font_date, fill=0, anchor="mm")
            draw.line([(10, 24), (PRINTER_WIDTH - 10, 24)], fill=0)
            final_img.paste(dithered, (0, caption_h))
        else:
            final_img.paste(dithered, (0, 0))
            draw.line([(10, dithered.height + 4), (PRINTER_WIDTH - 10, dithered.height + 4)], fill=0)
            draw.text((PRINTER_WIDTH // 2, dithered.height + 16), f"PRINTED: {now_str}", font=font_date, fill=0, anchor="mm")

        return final_img



def render_test_chart(
    show_datetime: bool = True,
    datetime_position: str = "footer",
) -> Image.Image:
    """Generate diagnostic print test chart with improved fonts and high-contrast dithering gradient."""
    w = PRINTER_WIDTH
    font_title = get_font(18, bold=True)
    font_info = get_font(13)
    font_info_bold = get_font(13, bold=True)
    font_small = get_font(11)
    font_date = get_font(12)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Extra height calculation
    extra_h = 28 if show_datetime else 0
    h = 390 + extra_h
    if h % 2 != 0:
        h += 1

    img = Image.new("1", (w, h), 1)
    draw = ImageDraw.Draw(img)

    y_offset = 0
    # Top border
    draw.rectangle([(0, 0), (w - 1, 3)], fill=0)

    # 1. Header with optional datetime
    if show_datetime and datetime_position == "header":
        draw.text((w // 2, 15), f"PRINTED: {now_str}", font=font_date, fill=0, anchor="mm")
        draw.line([(10, 26), (w - 10, 26)], fill=0)
        y_offset = 26

    draw.text((w // 2, y_offset + 16), "=== PRINTER TEST CHART ===", font=font_title, fill=0, anchor="mm")
    draw.text((w // 2, y_offset + 36), "SWS-PT1 (203 DPI / 384 dots)", font=font_info, fill=0, anchor="mm")
    draw.line([(10, y_offset + 48), (w - 10, y_offset + 48)], fill=0)

    # 2. Font Size Ladder
    draw.text((15, y_offset + 56), "8pt: あいうえお ABCDEFG 012345", font=get_font(12), fill=0)
    draw.text((15, y_offset + 74), "12pt: あいうえお ABCDEFG 012345", font=get_font(16), fill=0)
    draw.text((15, y_offset + 96), "16pt: かんたん印刷テスト", font=get_font(20), fill=0)
    draw.text((15, y_offset + 122), "20pt: ZiriZiri DTP", font=get_font(24, bold=True), fill=0)

    # 3. Dithering & Grayscale Gradient (0% -> 100%)
    draw.line([(10, y_offset + 158), (w - 10, y_offset + 158)], fill=0)
    draw.text((15, y_offset + 166), "Dithering Grayscale Gradient (0% - 100%):", font=font_info_bold, fill=0)

    # 10-step discrete gradient bar
    steps = 10
    grad_w = w - 30
    step_w = grad_w // steps
    bar_h = 22

    # Render discrete steps using true grayscale (L mode) and Floyd-Steinberg dithering
    step_img = Image.new("L", (grad_w, bar_h), 255)
    step_draw = ImageDraw.Draw(step_img)
    for s in range(steps):
        # 0% is white (255), 100% is solid black (0)
        gray_val = int(255 * (1.0 - s / (steps - 1)))
        bx = s * step_w
        step_draw.rectangle([(bx, 0), (bx + step_w, bar_h)], fill=gray_val)

    step_dithered = step_img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    img.paste(step_dithered, (15, y_offset + 188))

    # Draw step outline boxes
    for s in range(steps):
        bx = 15 + s * step_w
        by = y_offset + 188
        draw.rectangle([(bx, by), (bx + step_w, by + bar_h)], outline=0)

    # Step labels
    draw.text((15, y_offset + 213), "0%", font=font_small, fill=0)
    draw.text((15 + 5 * step_w, y_offset + 213), "55%", font=font_small, fill=0, anchor="ma")
    draw.text((15 + grad_w, y_offset + 213), "100%", font=font_small, fill=0, anchor="ra")

    # Continuous smooth gradient bar
    smooth_h = 16
    smooth_img = Image.new("L", (grad_w, smooth_h), 255)
    for x in range(grad_w):
        gray_val = int(255 * (1.0 - x / (grad_w - 1)))
        for y_pix in range(smooth_h):
            smooth_img.putpixel((x, y_pix), gray_val)
    smooth_dithered = smooth_img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    img.paste(smooth_dithered, (15, y_offset + 228))
    draw.rectangle([(15, y_offset + 228), (15 + grad_w, y_offset + 228 + smooth_h)], outline=0)

    # 4. Dot alignment & Ruler
    draw.line([(10, y_offset + 256), (w - 10, y_offset + 256)], fill=0)
    draw.text((15, y_offset + 264), "Resolution Ruler (10px / 50px ticks):", font=font_info_bold, fill=0)
    draw.line([(15, y_offset + 290), (w - 15, y_offset + 290)], fill=0, width=2)
    for x in range(15, w - 15, 10):
        tick_h = 10 if (x - 15) % 50 == 0 else 4
        draw.line([(x, y_offset + 290), (x, y_offset + 290 + tick_h)], fill=0, width=1)
        if (x - 15) % 50 == 0 and (x - 15) > 0:
            draw.text((x, y_offset + 303), str(x - 15), font=font_info, fill=0, anchor="mt")

    # Footer datetime
    if show_datetime and datetime_position == "footer":
        foot_y = y_offset + 338
        draw.line([(10, foot_y), (w - 10, foot_y)], fill=0)
        draw.text((w // 2, foot_y + 12), f"PRINTED: {now_str}", font=font_date, fill=0, anchor="mm")

    # 5. Bottom border
    draw.rectangle([(0, h - 4), (w - 1, h - 1)], fill=0)
    return img
