"""Configuration settings for ZiriZiriDTP."""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Printer Hardware Settings
PRINTER_MAC = os.getenv("PRINTER_MAC", "AA:BB:CC:DE:04:EF")
PRINTER_NAME = os.getenv("PRINTER_NAME", "SWS-PT1")
PRINTER_WIDTH = int(os.getenv("PRINTER_WIDTH", "384"))  # 384 dots (58mm width)
PRINTER_DPI = int(os.getenv("PRINTER_DPI", "203"))
DEFAULT_DENSITY = int(os.getenv("DEFAULT_DENSITY", "3"))  # 0 to 7
DEFAULT_FEED_AFTER = int(os.getenv("DEFAULT_FEED_AFTER", "40"))

# BLE GATT UUIDs
WRITE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"

# System Font Paths
DEFAULT_FONT_PATH = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"
FALLBACK_FONT_PATH = "/home/minamo/.local/share/fonts/BizinGothicDiscordNF-Regular.ttf"
