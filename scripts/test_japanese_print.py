import asyncio
from PIL import Image, ImageDraw, ImageFont
import sys
import os

# Use funnyprint package from scratch
sys.path.insert(0, os.path.abspath("scratch/funnyprint_gui"))
from funnyprint.service import PrintService
from funnyprint.imaging import pil_to_funny_lines

FONT_PATH = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"
PRINTER_WIDTH = 384

def create_japanese_receipt():
    w = PRINTER_WIDTH
    h = 240
    img = Image.new("1", (w, h), 1) # 1 = white
    draw = ImageDraw.Draw(img)

    font_large = ImageFont.truetype(FONT_PATH, 24)
    font_mid = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)

    # Header border
    draw.rectangle([(0, 0), (w-1, 4)], fill=0)

    # Title
    draw.text((w // 2, 25), "ZiriZiriDTP", font=font_large, fill=0, anchor="mm")
    draw.text((w // 2, 50), "サーマルプリンタ接続成功！", font=font_mid, fill=0, anchor="mm")

    # Separator
    draw.line([(10, 68), (w-10, 68)], fill=0, width=1)

    # TODO items
    draw.text((20, 80), "[x] Linux Bluetooth接続", font=font_small, fill=0)
    draw.text((20, 105), "[x] Funny Print認証クリア", font=font_small, fill=0)
    draw.text((20, 130), "[x] 日本語テキスト印字", font=font_small, fill=0)
    draw.text((20, 155), "[ ] スマホWeb画面の作成", font=font_small, fill=0)
    draw.text((20, 180), "[ ] お買い物メモ印刷", font=font_small, fill=0)

    # Footer border
    draw.rectangle([(0, h-4), (w-1, h-1)], fill=0)

    return img

def main():
    print("日本語レシート画像の生成中...")
    img = create_japanese_receipt()
    funny_lines = pil_to_funny_lines(img)

    svc = PrintService(on_log=print)
    try:
        print("プリンタに接続中...")
        fut = svc.run_async(svc.connect())
        if not fut.result(timeout=25):
            print("接続に失敗しました")
            return

        print("印刷実行中 (日本語TODOメモ)...")
        fut = svc.run_async(svc.print_lines(funny_lines, density=3, feed=40))
        fut.result(timeout=60)
        print("日本語印刷完了！")
    finally:
        try:
            svc.run_async(svc.disconnect()).result(timeout=5)
        except Exception:
            pass
        svc.stop()

if __name__ == "__main__":
    main()
