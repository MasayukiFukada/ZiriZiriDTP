import asyncio
import sys
from bleak import BleakClient

ADDRESS = "AA:BB:CC:DE:04:EF"
# Candidate characteristics for writing
FFE1_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
FF15_UUID = "0000ff15-0000-1000-8000-00805f9b34fb"

async def main():
    target_name = sys.argv[1] if len(sys.argv) > 1 else "ffe1"
    target_uuid = FFE1_UUID if target_name == "ffe1" else FF15_UUID

    payload = (
        b"\x1b@"  # ESC @ (Initialize)
        b"Hello ZiriZiriDTP!\n"
        b"SWS-PT1 Thermal Printer\n"
        b"Testing 1-2-3...\n"
        b"--------------------------------\n"
        b"Status: OK\n\n\n\n"
        b"\x1bd\x04"  # Feed 4 lines
    )

    print(f"Connecting to {ADDRESS}...")
    async with BleakClient(ADDRESS, timeout=15.0) as client:
        print(f"Connected! MTU: {client.mtu_size}")
        print(f"Writing payload to {target_name} ({target_uuid})...")
        
        # Send in MTU chunks
        chunk_size = max(20, client.mtu_size - 3)
        for i in range(0, len(payload), chunk_size):
            chunk = payload[i:i+chunk_size]
            await client.write_gatt_char(target_uuid, chunk, response=False)
            await asyncio.sleep(0.05)
        
        print("Data sent successfully!")
        await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(main())
