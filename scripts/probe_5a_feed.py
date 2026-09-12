import asyncio
from bleak import BleakClient, BleakScanner

ADDRESS = "AA:BB:CC:DE:04:EF"
WRITE_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"

# Paper feed candidates (Feed ~60-100 dots/lines)
# Format: 5A [CMD/DATA] ... 23 23
candidates = [
    # Pattern A: 5A <cmd> <len> <data...> 23 23
    ("Feed A1 (cmd 0x01, 60 lines)", bytes([0x5a, 0x01, 0x3c, 0x00, 0x23, 0x23])),
    ("Feed A2 (cmd 0x02, 60 lines)", bytes([0x5a, 0x02, 0x3c, 0x00, 0x23, 0x23])),
    ("Feed A3 (cmd 0x03, 60 lines)", bytes([0x5a, 0x03, 0x3c, 0x00, 0x23, 0x23])),
    ("Feed A4 (cmd 0xa1, 60 lines)", bytes([0x5a, 0xa1, 0x3c, 0x00, 0x23, 0x23])),
    ("Feed A5 (cmd 0xa3, 60 lines)", bytes([0x5a, 0xa3, 0x3c, 0x00, 0x23, 0x23])),
    
    # Pattern B: Fixed length matching status report (12 bytes)
    # 5A <cmd> <data: 8 bytes> 23 23
    ("Feed B1 (12 bytes cmd 0x01)", bytes([0x5a, 0x01, 0x3c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x23, 0x23])),
    ("Feed B2 (12 bytes cmd 0x03)", bytes([0x5a, 0x03, 0x3c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x23, 0x23])),
    ("Feed B3 (12 bytes cmd 0xa1)", bytes([0x5a, 0xa1, 0x3c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x23, 0x23])),

    # Pattern C: With length byte (5A <len> <cmd> <data...> <chk> 23 23)
    ("Feed C1 (len prefix)", bytes([0x5a, 0x04, 0x01, 0x3c, 0x00, 0x23, 0x23])),
    ("Feed C2 (len prefix 0x03)", bytes([0x5a, 0x04, 0x03, 0x3c, 0x00, 0x23, 0x23])),

    # Pattern D: Simple ESC d 3 wrapped in 5A ... 23 23
    ("Feed D1 (ESC d wrapped)", bytes([0x5a, 0x1b, 0x64, 0x05, 0x23, 0x23])),

    # Pattern E: WalkPrint feed line command (5A 08 ... 23 23)
    ("Feed E1 (WalkPrint 8-byte feed)", bytes([0x5a, 0x08, 0x00, 0x3c, 0x00, 0x00, 0x23, 0x23])),
]

def notify_cb(sender, data):
    val = data.hex()
    bat = data[2] if len(data) > 2 else "?"
    print(f"  <-- [REPLY/STATUS]: {val} (Battery: {bat}%)")

async def main():
    print(f"Connecting to {ADDRESS}...")
    device = await BleakScanner.find_device_by_address(ADDRESS, timeout=5.0)
    async with BleakClient(device or ADDRESS, timeout=10.0) as client:
        print("Connected!")
        await client.start_notify(NOTIFY_FFE2, notify_cb)
        await asyncio.sleep(0.5)

        for name, pkt in candidates:
            print(f"\n--> Sending {name} ({pkt.hex()})...")
            await client.write_gatt_char(WRITE_FFE1, pkt, response=False)
            # Wait 2 seconds to see if paper feeds
            await asyncio.sleep(2.0)

        print("\nAll candidates sent.")

if __name__ == "__main__":
    asyncio.run(main())
