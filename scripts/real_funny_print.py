import asyncio
import binascii
from PIL import Image, ImageDraw, ImageFont
from bleak import BleakClient, BleakScanner

MAC = "AA:BB:CC:DE:04:EF"
WRITE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"

PRINTER_WIDTH = 384

def _crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        for i in range(8):
            bit = (b >> (7 - i)) & 1
            c15 = (crc >> 15) & 1
            crc = (crc << 1) & 0xFFFF
            if c15 ^ bit:
                crc ^= 0x1021
    return crc

def pkt_hw() -> bytes:
    return b"\x5a\x01" + b"\x00" * 10

def pkt_challenge() -> bytes:
    return b"\x5a\x0a" + b"\x00" * 10

def pkt_response(mac: str) -> bytes:
    mac_hex = mac.replace(":", "")
    payload = b"\x00" + binascii.unhexlify(mac_hex)
    r = (_crc16(payload) >> 8) & 0xFF
    return b"\x5a\x0b" + bytes([r]) * 10

def pkt_density(d: int) -> bytes:
    return b"\x5a\x0c" + bytes([max(0, min(7, d))])

def pkt_print_event(num_lines: int, end: bool = False) -> bytes:
    return b"\x5a\x04" + num_lines.to_bytes(2, "big") + end.to_bytes(2, "little")

def pkt_print_line(line_no: int, data: bytes) -> bytes:
    return b"\x55" + line_no.to_bytes(2, "big") + data + b"\x00"

def create_sample_image():
    # Width 384, Height 160
    w, h = PRINTER_WIDTH, 160
    img = Image.new("1", (w, h), 1) # 1 = white
    draw = ImageDraw.Draw(img)

    # Frame
    draw.rectangle([(0, 0), (w-1, 6)], fill=0)

    # Text
    draw.text((20, 15), "=== ZiriZiriDTP Handshake OK ===", fill=0)
    draw.text((20, 38), "Printer: SWS-PT1 (Funny Print)", fill=0)
    draw.text((20, 60), "[X] Bleak BLE Connected", fill=0)
    draw.text((20, 82), "[X] Protocol Handshake Complete!", fill=0)
    draw.text((20, 104), "[ ] Enjoy Thermal Printing!", fill=0)

    # Pattern
    for x in range(20, 360, 20):
        draw.rectangle([(x, 130), (x+10, 148)], fill=0)

    draw.rectangle([(0, h-6), (w-1, h-1)], fill=0)
    return img

def pil_to_funny_lines(img_1bit):
    raw = img_1bit.tobytes()
    bpl = PRINTER_WIDTH // 8 # 48
    # Invert bits: black in 1-bit PIL is 0, thermal printer needs 1 for black
    lines = [bytes([b ^ 0xFF for b in raw[i : i + bpl]]) for i in range(0, len(raw), bpl)]
    result = []
    from itertools import islice
    it = iter(lines)
    while pair := tuple(islice(it, 2)):
        combined = bytearray(96)
        combined[: len(pair[0])] = pair[0]
        if len(pair) == 2:
            combined[48 : 48 + len(pair[1])] = pair[1]
        result.append(bytes(combined))
    return result

async def main():
    hs_queue = asyncio.Queue()
    ctrl_queue = asyncio.Queue()

    def on_notify(sender, data):
        pt = data[0:2]
        print(f"  <-- [NOTIFY]: {data.hex()}")
        if pt in (b"\x5a\x0a", b"\x5a\x0b"):
            hs_queue.put_nowait(data)
        elif pt == b"\x5a\x05":
            ln = int.from_bytes(data[2:4], "big")
            ctrl_queue.put_nowait(("lost", ln))
        elif pt == b"\x5a\x06":
            ctrl_queue.put_nowait(("done", 0))
        elif pt == b"\x5a\x08":
            ctrl_queue.put_nowait(("pause", 0))

    print(f"Connecting to {MAC}...")
    device = await BleakScanner.find_device_by_address(MAC, timeout=6.0)
    async with BleakClient(device or MAC, timeout=12.0) as client:
        print("Connected to SWS-PT1!")
        await client.start_notify(NOTIFY_UUID, on_notify)
        await asyncio.sleep(0.3)

        # 1. Handshake
        print("\n--- Handshake Phase 1 ---")
        await client.write_gatt_char(WRITE_UUID, pkt_hw(), response=False)
        await asyncio.sleep(0.3)
        await client.write_gatt_char(WRITE_UUID, pkt_challenge(), response=False)
        
        reply1 = await asyncio.wait_for(hs_queue.get(), timeout=5.0)
        print(f"Received Challenge Reply: {reply1.hex()}")

        print("\n--- Handshake Phase 2 ---")
        resp_pkt = pkt_response(MAC)
        print(f"Sending Response: {resp_pkt.hex()}")
        await client.write_gatt_char(WRITE_UUID, resp_pkt, response=False)

        reply2 = await asyncio.wait_for(hs_queue.get(), timeout=5.0)
        print(f"Received Auth Result: {reply2.hex()}")
        if reply2[2] == 0x01:
            print(">>> HANDSHAKE AUTHENTICATION SUCCESSFUL! <<<")
        else:
            print(f">>> Handshake status: {reply2[2]} (proceeding anyway)")

        # 2. Prepare print data
        img = create_sample_image()
        funny_lines = pil_to_funny_lines(img)
        # Add 40 blank lines for paper feed
        blank = bytes(96)
        for _ in range(20):
            funny_lines.append(blank)

        total_lines = len(funny_lines)
        print(f"\nPrinting {total_lines} chunks (density=3)...")

        # Set density
        await client.write_gatt_char(WRITE_UUID, pkt_density(3), response=False)
        await asyncio.sleep(0.2)

        # Start print session
        await client.write_gatt_char(WRITE_UUID, pkt_print_event(total_lines, end=False), response=False)
        await asyncio.sleep(0.1)

        # Send raster lines
        for i, line_data in enumerate(funny_lines):
            pkt = pkt_print_line(i, line_data)
            await client.write_gatt_char(WRITE_UUID, pkt, response=False)
            if i % 10 == 0:
                print(f"  Printing line {i}/{total_lines}...")
            await asyncio.sleep(0.025)

        # End print session
        await asyncio.sleep(0.5)
        await client.write_gatt_char(WRITE_UUID, pkt_print_event(total_lines, end=True), response=False)
        print("\nEnd print event sent! Waiting 3s for printer to finish...")
        await asyncio.sleep(3.0)
        print("All done!")

if __name__ == "__main__":
    asyncio.run(main())
