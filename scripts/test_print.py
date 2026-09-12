import subprocess
import time
import sys

def send_data_busctl(char_path, data_bytes):
    # data_bytes to array of bytes format for busctl:
    # busctl call org.bluez <path> org.bluez.GattCharacteristic1 WriteValue aya{sv} <len> <b0> <b1> ... 0
    cmd = [
        "busctl", "call", "org.bluez", char_path,
        "org.bluez.GattCharacteristic1", "WriteValue", "aya{sv}",
        str(len(data_bytes))
    ] + [str(b) for b in data_bytes] + ["0"]
    print(f"Sending {len(data_bytes)} bytes to {char_path}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error: {res.stderr}")
    else:
        print(f"Success: {res.stdout.strip()}")

def main():
    # ESC/POS commands:
    # 0x1b, 0x40 (ESC @: Initialize)
    # Text
    # 0x0a (LF)
    # 0x1b, 0x64, 0x03 (ESC d 3: Feed 3 lines)
    payload = b"\x1b@Hello ZiriZiriDTP!\nSWS-PT1 Thermal Printer\nTesting 1-2-3...\n\n\x1bd\x03"
    
    char_ffe1 = "/org/bluez/hci0/dev_AA_BB_CC_DE_04_EF/service0007/char0008" # 0000ffe1
    char_ff15 = "/org/bluez/hci0/dev_AA_BB_CC_DE_04_EF/service0001/char0002" # 0000ff15

    target = sys.argv[1] if len(sys.argv) > 1 else "ffe1"
    target_path = char_ffe1 if target == "ffe1" else char_ff15

    print(f"Testing write to {target} ({target_path})...")
    # BLE MTU is often around 20~244 bytes. Send in chunks of 20 bytes if needed.
    chunk_size = 20
    for i in range(0, len(payload), chunk_size):
        chunk = payload[i:i+chunk_size]
        send_data_busctl(target_path, chunk)
        time.sleep(0.05)

if __name__ == "__main__":
    main()
