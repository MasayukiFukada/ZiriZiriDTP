import asyncio
from bleak import BleakClient, BleakScanner

ADDRESS = "AA:BB:CC:DE:04:EF"
# Service 1: 0000ff12
WRITE_FF15 = "0000ff15-0000-1000-8000-00805f9b34fb"
NOTIFY_FF14 = "0000ff14-0000-1000-8000-00805f9b34fb"

# Service 2: 0000ffe6
WRITE_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"

def notify_cb14(sender, data):
    print(f"  <-- [NOTIFY from Service 1 (FF14)]: {data.hex()}")

def notify_cbE2(sender, data):
    print(f"  <-- [NOTIFY from Service 2 (FFE2)]: {data.hex()}")

async def main():
    print(f"Connecting to {ADDRESS}...")
    device = await BleakScanner.find_device_by_address(ADDRESS, timeout=5.0)
    async with BleakClient(device or ADDRESS, timeout=10.0) as client:
        print("Connected!")
        await client.start_notify(NOTIFY_FF14, notify_cb14)
        await client.start_notify(NOTIFY_FFE2, notify_cbE2)
        await asyncio.sleep(0.5)

        # Test sending Cmd 0x01 to FF15
        pkt_mac = bytes([0x5a, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x23, 0x23])
        print("\n--> Sending Cmd 0x01 to FF15 (Service 1)...")
        await client.write_gatt_char(WRITE_FF15, pkt_mac, response=False)
        await asyncio.sleep(1.0)

        # Test sending Cmd 0x01 to FFE1 (Service 2)
        print("\n--> Sending Cmd 0x01 to FFE1 (Service 2)...")
        await client.write_gatt_char(WRITE_FFE1, pkt_mac, response=False)
        await asyncio.sleep(1.0)

        # Check if FF15 accepts raw bytes or ESC/POS
        esc_test = b"\x1b@\nHello FF15\n\x1bd\x03"
        print("\n--> Sending ESC/POS to FF15...")
        await client.write_gatt_char(WRITE_FF15, esc_test, response=False)
        await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(main())
