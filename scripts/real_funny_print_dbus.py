import asyncio
import binascii
from PIL import Image, ImageDraw, ImageFont
from dbus_fast.aio import MessageBus
from dbus_fast import Message, MessageType, Variant, BusType

DEV_PATH = "/org/bluez/hci0/dev_AA_BB_CC_DE_04_EF"
WRITE_CHAR = f"{DEV_PATH}/service0007/char0008" # 0000ffe1
NOTIFY_CHAR = f"{DEV_PATH}/service0007/char000a" # 0000ffe2

MAC = "AA:BB:CC:DE:04:EF"
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
    w, h = PRINTER_WIDTH, 160
    img = Image.new("1", (w, h), 1)
    draw = ImageDraw.Draw(img)

    # Frame
    draw.rectangle([(0, 0), (w-1, 6)], fill=0)

    # Text
    draw.text((20, 15), "=== ZiriZiriDTP Handshake OK ===", fill=0)
    draw.text((20, 38), "Printer: SWS-PT1 (Funny Print)", fill=0)
    draw.text((20, 60), "[X] Linux BLE Connected", fill=0)
    draw.text((20, 82), "[X] Auth Handshake Succeeded!", fill=0)
    draw.text((20, 104), "[X] Real Thermal Print Output", fill=0)

    # Checker pattern
    for x in range(20, 360, 20):
        draw.rectangle([(x, 130), (x+10, 148)], fill=0)

    draw.rectangle([(0, h-6), (w-1, h-1)], fill=0)
    return img

def pil_to_funny_lines(img_1bit):
    raw = img_1bit.tobytes()
    bpl = PRINTER_WIDTH // 8
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
    print("Connecting to BlueZ System Bus...")
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    hs_queue = asyncio.Queue()
    ctrl_queue = asyncio.Queue()

    def on_message(msg):
        if msg.message_type == MessageType.SIGNAL and msg.member == "PropertiesChanged":
            iface, changed, invalidated = msg.body
            if "Value" in changed:
                val = bytes(changed["Value"].value)
                pt = val[0:2]
                print(f"  <-- [NOTIFY]: {val.hex()}")
                if pt in (b"\x5a\x0a", b"\x5a\x0b"):
                    hs_queue.put_nowait(val)
                elif pt == b"\x5a\x05":
                    ln = int.from_bytes(val[2:4], "big")
                    ctrl_queue.put_nowait(("lost", ln))
                elif pt == b"\x5a\x06":
                    ctrl_queue.put_nowait(("done", 0))
                elif pt == b"\x5a\x08":
                    ctrl_queue.put_nowait(("pause", 0))

    bus.add_message_handler(on_message)

    # StartNotify
    msg = Message(
        destination="org.bluez",
        path=NOTIFY_CHAR,
        interface="org.bluez.GattCharacteristic1",
        member="StartNotify"
    )
    await bus.call(msg)
    print("Subscribed to NOTIFY!")

    async def write_bytes(data):
        m = Message(
            destination="org.bluez",
            path=WRITE_CHAR,
            interface="org.bluez.GattCharacteristic1",
            member="WriteValue",
            signature="aya{sv}",
            body=[data, {"type": Variant("s", "command")}]
        )
        await bus.call(m)

    # 1. Handshake Phase 1
    print("\n--- Handshake Phase 1 ---")
    await write_bytes(pkt_hw())
    await asyncio.sleep(0.3)
    await write_bytes(pkt_challenge())

    try:
        reply1 = await asyncio.wait_for(hs_queue.get(), timeout=5.0)
        print(f"Received Challenge Reply: {reply1.hex()}")
    except asyncio.TimeoutError:
        print("Timeout waiting for challenge reply")

    # 2. Handshake Phase 2
    print("\n--- Handshake Phase 2 ---")
    resp_pkt = pkt_response(MAC)
    print(f"Sending Response: {resp_pkt.hex()}")
    await write_bytes(resp_pkt)

    try:
        reply2 = await asyncio.wait_for(hs_queue.get(), timeout=5.0)
        print(f"Received Auth Result: {reply2.hex()}")
        if len(reply2) > 2 and reply2[2] == 0x01:
            print(">>> HANDSHAKE AUTHENTICATION SUCCESSFUL! <<<")
        else:
            print(f">>> Auth status: {reply2.hex()}")
    except asyncio.TimeoutError:
        print("Timeout waiting for auth result")

    # 3. Print
    img = create_sample_image()
    funny_lines = pil_to_funny_lines(img)
    # Add 30 blank chunks for paper feed
    blank = bytes(96)
    for _ in range(30):
        funny_lines.append(blank)

    total_lines = len(funny_lines)
    print(f"\nPrinting {total_lines} chunks (density=3)...")

    # Density
    await write_bytes(pkt_density(3))
    await asyncio.sleep(0.3)

    # Print Event Start
    await write_bytes(pkt_print_event(total_lines, end=False))
    await asyncio.sleep(0.1)

    # Send Lines (Note: BLE MTU is typically 20, but BlueZ WriteValue automatically chunks or handles L2CAP)
    # Actually, if the characteristic accepts 99 bytes (0x55 + 2B + 96B + 0x00), let's send line packets
    for i, line_data in enumerate(funny_lines):
        pkt = pkt_print_line(i, line_data)
        await write_bytes(pkt)
        if i % 10 == 0:
            print(f"  Line {i}/{total_lines} sent...")
        await asyncio.sleep(0.035)

    # Print Event End
    await asyncio.sleep(0.5)
    await write_bytes(pkt_print_event(total_lines, end=True))
    print("\nEnd print event sent! Waiting 5s for mechanical output...")
    await asyncio.sleep(5.0)
    print("Complete!")

if __name__ == "__main__":
    asyncio.run(main())
