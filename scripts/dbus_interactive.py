import asyncio
from dbus_fast.aio import MessageBus
from dbus_fast import Message, MessageType, Variant, BusType

DEV_PATH = "/org/bluez/hci0/dev_AA_BB_CC_DE_04_EF"
FFE2_CHAR = f"{DEV_PATH}/service0007/char000a" # Notify
FFE1_CHAR = f"{DEV_PATH}/service0007/char0008" # Write
FF14_CHAR = f"{DEV_PATH}/service0001/char0004" # Notify
FF15_CHAR = f"{DEV_PATH}/service0001/char0002" # Write

async def main():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    print("Connected to System Bus.")

    # Match rule for PropertiesChanged signals (notifications)
    def on_message(msg):
        if msg.message_type == MessageType.SIGNAL and msg.member == "PropertiesChanged":
            iface, changed, invalidated = msg.body
            if "Value" in changed:
                val_bytes = bytes(changed["Value"].value)
                print(f"\n>>> [NOTIFY from {msg.path}]: {val_bytes.hex()} ({val_bytes})")

    bus.add_message_handler(on_message)

    # StartNotify on both notify characteristics
    for char_path in [FFE2_CHAR, FF14_CHAR]:
        msg = Message(
            destination="org.bluez",
            path=char_path,
            interface="org.bluez.GattCharacteristic1",
            member="StartNotify"
        )
        reply = await bus.call(msg)
        print(f"StartNotify on {char_path}: {reply.message_type.name}")

    async def write_char(char_path, payload):
        print(f"Writing {payload.hex()} to {char_path}...")
        msg = Message(
            destination="org.bluez",
            path=char_path,
            interface="org.bluez.GattCharacteristic1",
            member="WriteValue",
            signature="aya{sv}",
            body=[payload, {"type": Variant("s", "command")}]
        )
        await bus.call(msg)

    # Packets to test
    packets = [
        # Cat printer status query
        ("Cat Status 0xa3", bytes([0x51, 0x78, 0xa3, 0x00, 0x01, 0x00, 0x00, 0x00, 0xff])),
        ("Cat Status 0xbe", bytes([0x51, 0x78, 0xbe, 0x00, 0x01, 0x00, 0x00, 0x00, 0xff])),
        # DLE EOT status query
        ("ESC/POS DLE EOT", bytes([0x10, 0x04, 0x01])),
        ("ESC/POS DLE EOT 2", bytes([0x10, 0x04, 0x02])),
        # FunPrint / XQP
        ("XQP 1F 11 01", bytes([0x1f, 0x11, 0x01])),
        ("XQP 1F 11 11 Feed", bytes([0x1f, 0x11, 0x11, 0x30])),
    ]

    for target_name, target_path in [("ffe1", FFE1_CHAR), ("ff15", FF15_CHAR)]:
        print(f"\n--- Testing Writes to {target_name} ---")
        for desc, pkt in packets:
            print(f"[{desc}]")
            await write_char(target_path, pkt)
            await asyncio.sleep(1.0)

    print("\nListening for 5 seconds...")
    await asyncio.sleep(5.0)

if __name__ == "__main__":
    asyncio.run(main())
