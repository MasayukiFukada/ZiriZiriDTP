import asyncio
from bleak import BleakClient

ADDRESS = "AA:BB:CC:DE:04:EF"

async def main():
    print(f"Connecting to {ADDRESS}...")
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")
        for service in client.services:
            print(f"\n[Service] {service.uuid} - {service.description}")
            for char in service.characteristics:
                props = ", ".join(char.properties)
                print(f"  [Char] {char.uuid} ({props}) - {char.description}")
                for desc in char.descriptors:
                    print(f"    [Desc] {desc.uuid}: {desc.handle}")

if __name__ == "__main__":
    asyncio.run(main())
