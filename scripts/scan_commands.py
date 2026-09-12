import asyncio
from bleak import BleakClient, BleakScanner

ADDRESS = "AA:BB:CC:DE:04:EF"
WRITE_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"

last_reply = None

def notify_cb(sender, data):
    global last_reply
    last_reply = data.hex()
    print(f"    <-- [REPLY]: {last_reply}")

async def main():
    global last_reply
    print(f"Connecting to {ADDRESS}...")
    device = await BleakScanner.find_device_by_address(ADDRESS, timeout=5.0)
    async with BleakClient(device or ADDRESS, timeout=10.0) as client:
        print("Connected!")
        await client.start_notify(NOTIFY_FFE2, notify_cb)
        await asyncio.sleep(0.5)

        # Scan command IDs from 0x01 to 0x20
        # Format: 5A <cmd> 00 00 00 00 00 00 00 00 23 23 (12 bytes)
        for cmd in range(0x01, 0x21):
            pkt = bytes([0x5a, cmd, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x23, 0x23])
            last_reply = None
            print(f"--> Testing Cmd 0x{cmd:02x} ({pkt.hex()})...")
            await client.write_gatt_char(WRITE_FFE1, pkt, response=False)
            await asyncio.sleep(0.4)

        # Also test commands with some parameter (e.g. 0x3c = 60 lines)
        for cmd in [0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c]:
            pkt = bytes([0x5a, cmd, 0x3c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x23, 0x23])
            print(f"--> Testing Cmd 0x{cmd:02x} with param 0x3c ({pkt.hex()})...")
            await client.write_gatt_char(WRITE_FFE1, pkt, response=False)
            await asyncio.sleep(0.4)

if __name__ == "__main__":
    asyncio.run(main())
