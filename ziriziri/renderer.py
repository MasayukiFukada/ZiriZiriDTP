"""Image and receipt rendering engine for thermal printing."""

import base64
import urllib.parse
from io import BytesIO
from itertools import islice
from typing import List, Optional
from datetime import datetime

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ziriziri.config import PRINTER_WIDTH, DEFAULT_FONT_PATH, FALLBACK_FONT_PATH


def make_todo_qr(
    data: str,
    max_size: int = 220,
    border: int = 3,
    error_correction: int = qrcode.constants.ERROR_CORRECT_M,
) -> Image.Image:
    """Generate 1-bit QR code optimized for thermal receipt items.

    Tries larger box sizes (from 6 down to 2) to maximize module readability.
    Avoids NEAREST-neighbor resizing whenever possible to keep module widths uniform.
    """
    for bs in [6, 5, 4, 3, 2]:
        qr = qrcode.QRCode(
            version=None,
            error_correction=error_correction,
            box_size=bs,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("1")
        if img.width <= max_size:
            return img

    # If still larger than max_size with bs=2, retry with lower error correction or tighter border
    if border > 2 or error_correction != qrcode.constants.ERROR_CORRECT_L:
        for bs in [3, 2]:
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=bs,
                border=2,
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("1")
            if img.width <= max_size:
                return img

    if img.width > max_size:
        img = img.resize((max_size, max_size), Image.Resampling.NEAREST)
    return img


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    """Wrap text into multiple lines fitting within max_width."""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines or [""]


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


def draw_cut_line_separator(draw: ImageDraw.ImageDraw, y: int, w: int = PRINTER_WIDTH) -> None:
    """Draw an inline dashed scissors cut line across the receipt."""
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
    draw_cut_line_separator(draw, y, w)

    new_img.info.update(img.info)
    return new_img


def render_todo_receipt(
    title: str = "TODO LIST",
    items: Optional[List[dict]] = None,
    footer_text: Optional[str] = None,
    show_datetime: bool = True,
    datetime_position: str = "header",
) -> Image.Image:
    """Render receipt style TODO / Shopping list with optional QR codes and timestamp."""
    items = items or []
    w = PRINTER_WIDTH
    font_title = get_font(26, bold=True)
    font_date = get_font(13)
    font_item = get_font(16)
    font_sub = get_font(12)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Pre-process items and calculate layout
    rendered_items = []
    total_items_h = 0

    for itm in items:
        checked = itm.get("checked", False)
        text = itm.get("text", "")
        qr_type = itm.get("qr_type")
        qr_data = (itm.get("qr_data") or "").strip()

        qr_img = None
        if qr_data:
            try:
                qr_img = make_todo_qr(qr_data, max_size=210, border=3)
            except Exception:
                qr_img = None

        text_lines = wrap_text(text, font_item, max_width=315)
        badge_label = ""
        if qr_img:
            if qr_type == "url":
                badge_label = "[URL]"
            elif qr_type == "map":
                badge_label = "[地図]"
            elif qr_type == "memo":
                badge_label = "[メモ]"

            text_h = len(text_lines) * 22 + (18 if badge_label else 0) + 6
            qr_spacing = 8 + qr_img.height + 12
            item_h = max(text_h + qr_spacing, 44)
            rendered_items.append({
                "checked": checked,
                "text_lines": text_lines,
                "badge_label": badge_label,
                "qr_img": qr_img,
                "height": item_h,
            })
            total_items_h += item_h
        else:
            item_h = max(32, len(text_lines) * 22 + 10)
            rendered_items.append({
                "checked": checked,
                "text_lines": text_lines,
                "badge_label": "",
                "qr_img": None,
                "height": item_h,
            })
            total_items_h += item_h

    if not rendered_items:
        total_items_h = 32

    header_h = 80 if (show_datetime and datetime_position == "header") else 60
    footer_h = 60 if (show_datetime and datetime_position == "footer") else 46
    total_h = header_h + total_items_h + footer_h
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
    for itm in rendered_items:
        checked = itm["checked"]
        text_lines = itm["text_lines"]
        badge = itm["badge_label"]
        qr_img = itm["qr_img"]
        item_h = itm["height"]

        # Checkbox square (16x16)
        bx, by = 20, y + 4
        draw.rectangle([(bx, by), (bx + 16, by + 16)], fill=1, outline=0, width=2)
        if checked:
            draw.line([(bx + 3, by + 8), (bx + 7, by + 13)], fill=0, width=2)
            draw.line([(bx + 7, by + 13), (bx + 14, by + 3)], fill=0, width=2)

        # Text lines
        ty = y + 2
        for line in text_lines:
            draw.text((45, ty), line, font=font_item, fill=0)
            if checked:
                text_bbox = draw.textbbox((45, ty), line, font=font_item)
                strike_y = (text_bbox[1] + text_bbox[3]) // 2
                draw.line([(42, strike_y), (text_bbox[2] + 4, strike_y)], fill=0, width=1)
            ty += 22

        if badge:
            draw.text((45, ty + 1), badge, font=font_sub, fill=0)
            ty += 18

        # Centered large QR code below item text
        if qr_img:
            qr_x = (w - qr_img.width) // 2
            qr_y = ty + 6
            img.paste(qr_img, (qr_x, qr_y))

            # Draw subtle dotted separator below QR items
            sep_line_y = y + item_h - 2
            for sx in range(16, w - 16, 5):
                draw.line([(sx, sep_line_y), (sx + 2, sep_line_y)], fill=0, width=1)

        y += item_h

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


def build_gmaps_url(destination: str, travel_mode: str = "driving", action: str = "navigate") -> str:
    """Build a Google Maps universal URL for directions/navigation or search.

    Parameters:
        destination: Target place name, address, or 'lat,lng'.
        travel_mode: 'driving', 'bicycling', 'walking', 'transit'.
        action: 'navigate' (direct turn-by-turn navigation) or 'search' (place overview).
    """
    dest = (destination or "").strip()
    if not dest:
        return "https://www.google.com/maps"
    encoded_dest = urllib.parse.quote(dest)

    if action == "search":
        return f"https://www.google.com/maps/search/?api=1&query={encoded_dest}"

    mode = travel_mode if travel_mode in ("driving", "bicycling", "walking", "transit") else "driving"
    return f"https://www.google.com/maps/dir/?api=1&destination={encoded_dest}&travelmode={mode}&dir_action=navigate"


def render_route_sheet(
    title: str = "🚗 ドライブルート",
    items: Optional[List[dict]] = None,
    travel_mode: str = "driving",
    footer_text: Optional[str] = "ZiriZiriDTP * Safe Trip!",
    show_datetime: bool = True,
    datetime_position: str = "header",
    show_cut_line: bool = True,
) -> Image.Image:
    """Render a travel/drive route sheet with turn-by-turn Google Maps navigation QR codes.

    Layout per stop:
    - Step index [01], Checkbox [ ], Destination Name (bold, wrapped), Note, Action badge
    - Right side: Scan-optimized QR code for instant navigation launcher
    - Between stops: Route connector arrow/line (↓)
    """
    w = PRINTER_WIDTH
    items = items or []

    font_title = get_font(20, bold=True)
    font_badge = get_font(12, bold=True)
    font_name = get_font(16, bold=True)
    font_note = get_font(12)
    font_small = get_font(11)
    font_date = get_font(12)
    font_sub = get_font(12)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    mode_labels = {
        "driving": "車 / DRIVING 🚗",
        "bicycling": "自転車 / BIKING 🚲",
        "walking": "徒歩 / WALKING 🚶",
        "transit": "交通機関 / TRANSIT 🚃",
    }
    mode_str = mode_labels.get(travel_mode, travel_mode.upper())

    # Pre-process items
    rendered_items = []
    total_items_h = 0

    for idx, itm in enumerate(items, 1):
        name = (itm.get("name") or "").strip()
        location = (itm.get("location") or name).strip()
        note = (itm.get("note") or "").strip()
        checked = itm.get("checked", False)
        action = itm.get("action", "navigate")

        # Generate Navigation QR
        url = build_gmaps_url(location, travel_mode=travel_mode, action=action)
        try:
            qr_img = make_todo_qr(url, max_size=200, border=3)
        except Exception:
            qr_img = None

        action_label = "[ナビ起動]" if action == "navigate" else "[地図詳細]"

        # Text wrap: text can use full width now
        max_text_w = 295
        name_lines = wrap_text(name or location or f"スポット {idx}", font_name, max_width=max_text_w)
        note_lines = wrap_text(note, font_note, max_width=max_text_w) if note else []

        # Calculate height for this step
        text_h = len(name_lines) * 22 + (len(note_lines) * 16) + 20 + 4
        qr_h = (qr_img.height + 14) if qr_img else 0
        step_h = text_h + qr_h

        # Space for connecting connector line or inline cut separator
        has_next = (idx < len(items))
        is_cut_point = (idx % 2 == 0 and has_next)
        if is_cut_point:
            spacing_h = 36  # Inline scissors cut line separator
        elif has_next:
            spacing_h = 16  # Connector arrow height
        else:
            spacing_h = 0

        rendered_items.append({
            "idx": idx,
            "checked": checked,
            "name_lines": name_lines,
            "note_lines": note_lines,
            "action_label": action_label,
            "qr_img": qr_img,
            "step_h": step_h,
            "spacing_h": spacing_h,
            "is_cut_point": is_cut_point,
        })
        total_items_h += step_h + spacing_h

    if not rendered_items:
        total_items_h = 44

    header_h = 92 if (show_datetime and datetime_position == "header") else 72
    footer_h = 62 if (show_datetime and datetime_position == "footer") else 46
    total_h = header_h + total_items_h + footer_h
    if total_h % 2 != 0:
        total_h += 1

    img = Image.new("1", (w, total_h), 1)
    draw = ImageDraw.Draw(img)

    # Header decorative borders
    draw.rectangle([(0, 0), (w - 1, 4)], fill=0)
    draw.rectangle([(0, 7), (w - 1, 9)], fill=0)

    # Title & Travel mode
    draw.text((w // 2, 26), title, font=font_title, fill=0, anchor="mm")
    draw.text((w // 2, 48), f"MODE: {mode_str}", font=font_badge, fill=0, anchor="mm")

    sep_y = 58
    if show_datetime and datetime_position == "header":
        draw.text((w // 2, 68), now_str, font=font_date, fill=0, anchor="mm")
        sep_y = 80

    # Header separator dotted line
    for x in range(12, w - 12, 6):
        draw.line([(x, sep_y), (x + 3, sep_y)], fill=0, width=1)

    # Track pause points for printer cooling pacing
    pause_chunks = []

    # Render items
    y = sep_y + 10
    if not rendered_items:
        draw.text((w // 2, y + 10), "（経由地・目的地が登録されていません）", font=font_note, fill=0, anchor="mm")
        y += 34
    else:
        for itm in rendered_items:
            idx = itm["idx"]
            checked = itm["checked"]
            name_lines = itm["name_lines"]
            note_lines = itm["note_lines"]
            action_label = itm["action_label"]
            qr_img = itm["qr_img"]
            step_h = itm["step_h"]
            spacing_h = itm["spacing_h"]
            is_cut_point = itm["is_cut_point"]

            # Step index badge [01]
            badge_text = f"[{idx:02d}]"
            draw.text((12, y + 4), badge_text, font=font_badge, fill=0)

            # Checkbox square (16x16)
            bx, by = 46, y + 4
            draw.rectangle([(bx, by), (bx + 16, by + 16)], fill=1, outline=0, width=2)
            if checked:
                draw.line([(bx + 3, by + 8), (bx + 7, by + 13)], fill=0, width=2)
                draw.line([(bx + 7, by + 13), (bx + 14, by + 3)], fill=0, width=2)

            # Text content
            ty = y + 2
            for line in name_lines:
                draw.text((70, ty), line, font=font_name, fill=0)
                ty += 22

            for nline in note_lines:
                draw.text((70, ty), nline, font=font_note, fill=0)
                ty += 16

            # Action tag [ナビ起動] or [地図詳細]
            draw.text((70, ty), action_label, font=font_small, fill=0)
            ty += 18

            # Centered large QR code
            if qr_img:
                qr_x = (w - qr_img.width) // 2
                qr_y = ty + 4
                img.paste(qr_img, (qr_x, qr_y))

            y += step_h

            # Inline cut separator or connector arrow between steps
            if is_cut_point:
                cut_y = y + spacing_h // 2
                draw_cut_line_separator(draw, cut_y, w)
                pause_chunks.append({
                    "chunk": (y + spacing_h) // 2,
                    "finished_spots": f"{idx - 1:02d}〜{idx:02d}",
                    "next_spots": f"{idx + 1:02d}〜{min(idx + 2, len(items)):02d}",
                })
                y += spacing_h
            elif spacing_h > 0:
                cx = 54  # Align with checkbox center
                draw.line([(cx, y - 2), (cx, y + spacing_h - 4)], fill=0, width=2)
                draw.line([(cx - 3, y + spacing_h - 7), (cx, y + spacing_h - 4)], fill=0, width=2)
                draw.line([(cx + 3, y + spacing_h - 7), (cx, y + spacing_h - 4)], fill=0, width=2)
                y += spacing_h

    # Footer separator
    draw.line([(12, y + 6), (w - 12, y + 6)], fill=0, width=1)

    # Footer content
    fy = y + 20
    if show_datetime and datetime_position == "footer":
        draw.text((w // 2, fy), now_str, font=font_date, fill=0, anchor="mm")
        fy += 18

    f_text = footer_text or "ZiriZiriDTP * Safe Trip!"
    draw.text((w // 2, fy), f_text, font=font_sub, fill=0, anchor="mm")

    # Bottom border
    draw.rectangle([(0, total_h - 4), (w - 1, total_h - 1)], fill=0)

    img.info["pause_chunks"] = pause_chunks

    if show_cut_line:
        img = append_cut_line(img)

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
