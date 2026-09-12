import asyncio
from bleak import BleakClient, BleakScanner

ADDRESS = "AA:BB:CC:DE:04:EF"
NOTIFY_FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"
NOTIFY_FF14 = "0000ff14-0000-1000-8000-00805f9b34fb"

def notify_cb(sender, data):
    print(f"NOTIFY from handle/uuid {sender}: {data.hex()}")

async def main():
    device = await BleakScanner.find_device_by_address(ADDRESS, timeout=5.0)
    async with BleakClient(device or ADDRESS, timeout=10.0) as client:
        print("Connected!")
        for n in [NOTIFY_FFE2, NOTIFY_FF14]:
            try:
                await client.start_notify(n, notify_cb)
                print(f"Subscribed to {n}")
            except Exception as e:
                print(f"Error {n}: {e}")
        
        print("Listening for 3 seconds...")
        await asyncio.sleep(3.0)

if __name__ == "__main__":
    asyncio.run(main())
