import asyncio
import sys
from bleak import BleakClient

ADDRESS = "AA:BB:CC:DE:04:EF"

# Services & Characteristics
# Service 1: 0000ff12
WRITE_FF15 = "0000ff15-0000-1000-8000-00805f9b34fb"
NOTIFY_FF14 = "0000ff14-0000-1000-8000-00805f9b34fb"

# Service 2: 0000ffe6
WRITE_FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"

responses = []

def notification_handler(sender, data):
    print(f"\n[RECEIVED NOTIFICATION from {sender}]: {data.hex()} ({data})")
    responses.append((sender, data))

async def main():
    print(f"Connecting to {ADDRESS} via Bleak...")
    async with BleakClient(ADDRESS, timeout=10.0) as client:
        print(f"Connected: {client.is_connected}")
        
        # Subscribe to both notify characteristics
        for notify_uuid in [NOTIFY_FF14, NOTIFY_FFE2]:
            try:
                await client.start_notify(notify_uuid, notification_handler)
                print(f"Subscribed to notify on {notify_uuid}")
            except Exception as e:
                print(f"Failed to subscribe {notify_uuid}: {e}")

        # Test packets to send
        test_packets = [
            # 1. Cat printer status query (0xa3 or 0xbe)
            ("Cat Status 0xA3", bytes([0x51, 0x78, 0xa3, 0x00, 0x01, 0x00, 0x00, 0x00, 0xff])),
            ("Cat Status 0xBE", bytes([0x51, 0x78, 0xbe, 0x00, 0x01, 0x00, 0x00, 0x00, 0xff])),
            # 2. ESC/POS DLE EOT status query
            ("ESC/POS DLE EOT 1", bytes([0x10, 0x04, 0x01])),
            ("ESC/POS DLE EOT 2", bytes([0x10, 0x04, 0x02])),
            ("ESC/POS GS I 1", bytes([0x1d, 0x49, 0x01])),
            # 3. FunPrint / XQP probe
            ("XQP Get Status 1F 11 01", bytes([0x1f, 0x11, 0x01])),
            ("XQP 10 FF 20", bytes([0x10, 0xff, 0x20, 0x00])),
            # 4. Wakeup / Keepalive
            ("Wakeup zero bytes", bytes([0x00] * 8)),
        ]

        for write_name, write_uuid in [("ffe1", WRITE_FFE1), ("ff15", WRITE_FF15)]:
            print(f"\n=== Testing Writes to {write_name} ({write_uuid}) ===")
            for name, pkt in test_packets:
                print(f"Sending {name} ({pkt.hex()})...")
                try:
                    await client.write_gatt_char(write_uuid, pkt, response=False)
                except Exception as e:
                    print(f"Write error: {e}")
                await asyncio.sleep(0.5)

        print("\nWaiting 3 seconds for any remaining notifications...")
        await asyncio.sleep(3.0)

        print(f"\nTotal notifications received: {len(responses)}")

if __name__ == "__main__":
    asyncio.run(main())
