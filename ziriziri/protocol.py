"""Packet protocol definitions for FunnyPrint (Xiqi / SWS-PT1) thermal printer."""

import binascii

CHALLENGE = b"\x00" * 10


def crc16_xmodem(data: bytes) -> int:
    """Calculate CRC-16 (XMODEM) for FunnyPrint authentication."""
    crc = 0
    for b in data:
        for i in range(8):
            bit = (b >> (7 - i)) & 1
            c15 = (crc >> 15) & 1
            crc = (crc << 1) & 0xFFFF
            if c15 ^ bit:
                crc ^= 0x1021
    return crc


def pkt_hardware_info() -> bytes:
    """Request device hardware info."""
    return b"\x5a\x01" + b"\x00" * 10


def pkt_challenge() -> bytes:
    """Handshake step 1: send challenge packet."""
    return b"\x5a\x0a" + CHALLENGE


def pkt_response(mac: str) -> bytes:
    """Handshake step 2: send response based on MAC address and CRC16."""
    mac_hex = mac.replace(":", "")
    payload = CHALLENGE[0:1] + binascii.unhexlify(mac_hex)
    response_byte = (crc16_xmodem(payload) >> 8) & 0xFF
    return b"\x5a\x0b" + bytes([response_byte]) * 10


def pkt_density(density: int) -> bytes:
    """Set print darkness / energy (0-7)."""
    return b"\x5a\x0c" + bytes([max(0, min(7, density))])


def pkt_print_event(num_lines: int, end: bool = False) -> bytes:
    """Start (end=False) or Finish (end=True) print session."""
    return (
        b"\x5a\x04"
        + num_lines.to_bytes(2, "big")
        + end.to_bytes(2, "little")
    )


def pkt_print_line(line_no: int, data: bytes) -> bytes:
    """Send one line of raster data (96 bytes = 2 physical lines of 384 dots)."""
    return b"\x55" + line_no.to_bytes(2, "big") + data + b"\x00"
