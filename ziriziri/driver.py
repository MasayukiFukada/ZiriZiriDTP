"""Bluetooth Low Energy printer driver for SWS-PT1."""

import asyncio
from typing import Callable, Optional
from bleak import BleakClient, BleakScanner

from ziriziri.config import (
    PRINTER_MAC,
    PRINTER_NAME,
    WRITE_UUID,
    NOTIFY_UUID,
    DEFAULT_DENSITY,
    DEFAULT_FEED_AFTER,
)
from ziriziri.protocol import (
    pkt_hardware_info,
    pkt_challenge,
    pkt_response,
    pkt_density,
    pkt_print_event,
    pkt_print_line,
)


class PrinterDriver:
    """Manages BLE connection, handshake authentication, and print jobs."""

    def __init__(
        self,
        mac: str = PRINTER_MAC,
        name: str = PRINTER_NAME,
        on_log: Optional[Callable[[str], None]] = None,
    ):
        self.mac = mac
        self.name = name
        self.log = on_log or print
        self._lock: Optional[asyncio.Lock] = None
        self._hs_queue: Optional[asyncio.Queue] = None
        self._ctrl_queue: Optional[asyncio.Queue] = None
        self.battery: Optional[int] = None
        self.firmware_version: Optional[str] = None
        self.is_connected = False

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def hs_queue(self) -> asyncio.Queue:
        if self._hs_queue is None:
            self._hs_queue = asyncio.Queue()
        return self._hs_queue

    @property
    def ctrl_queue(self) -> asyncio.Queue:
        if self._ctrl_queue is None:
            self._ctrl_queue = asyncio.Queue()
        return self._ctrl_queue

    def _on_notify(self, sender: int, data: bytearray):
        pt = data[0:2]
        if pt in (b"\x5a\x0a", b"\x5a\x0b"):
            self.hs_queue.put_nowait(bytes(data))
        elif pt == b"\x5a\x05":
            ln = int.from_bytes(data[2:4], "big")
            self.ctrl_queue.put_nowait(("lost", ln))
        elif pt == b"\x5a\x06":
            self.ctrl_queue.put_nowait(("done", 0))
        elif pt == b"\x5a\x08":
            self.ctrl_queue.put_nowait(("pause", 0))
        elif pt == b"\x5a\x02":
            self.battery = data[2]
            if len(data) >= 10:
                self.firmware_version = f"{data[8]}.{data[9]:02d}"

    async def _connect_and_auth(self, client: BleakClient) -> bool:
        """Subscribe notifications and execute 2-phase handshake."""
        await client.start_notify(NOTIFY_UUID, self._on_notify)
        await asyncio.sleep(0.3)

        # 1. Hardware info request
        await client.write_gatt_char(WRITE_UUID, pkt_hardware_info(), response=False)
        await asyncio.sleep(0.3)

        # 2. Challenge phase
        await client.write_gatt_char(WRITE_UUID, pkt_challenge(), response=False)
        try:
            await asyncio.wait_for(self.hs_queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            self.log("Timeout waiting for handshake challenge reply.")
            return False

        # 3. Response phase
        await client.write_gatt_char(WRITE_UUID, pkt_response(self.mac), response=False)
        try:
            auth_result = await asyncio.wait_for(self.hs_queue.get(), timeout=5.0)
            if len(auth_result) > 2 and auth_result[2] == 0x01:
                self.log(f"Handshake successful. Battery: {self.battery}%")
                return True
            else:
                self.log(f"Handshake returned non-zero status: {auth_result.hex()}")
                return True  # Often still functional
        except asyncio.TimeoutError:
            self.log("Timeout waiting for handshake auth result.")
            return False

    async def get_status(self) -> dict:
        """Check printer status (quick connect & read battery)."""
        async with self.lock:
            # If we recently got battery, return it, or try a quick fetch
            try:
                device = await BleakScanner.find_device_by_address(self.mac, timeout=4.0)
                if not device:
                    return {
                        "connected": False,
                        "battery": self.battery,
                        "name": self.name,
                        "mac": self.mac,
                        "error": "Printer in sleep or out of range"
                    }

                async with BleakClient(device, timeout=8.0) as client:
                    await client.start_notify(NOTIFY_UUID, self._on_notify)
                    await client.write_gatt_char(WRITE_UUID, pkt_hardware_info(), response=False)
                    await asyncio.sleep(1.2)
                    return {
                        "connected": True,
                        "mac": self.mac,
                        "name": self.name,
                        "battery": self.battery,
                        "version": self.firmware_version,
                    }
            except Exception as e:
                return {
                    "connected": False,
                    "battery": self.battery,
                    "name": self.name,
                    "mac": self.mac,
                    "error": str(e),
                }


    async def print_chunks(
        self,
        chunks: list[bytes],
        density: int = DEFAULT_DENSITY,
        feed_after: int = DEFAULT_FEED_AFTER,
        on_progress: Optional[Callable[[int, int], None]] = None,
        pause_chunks: Optional[list] = None,
        pause_duration: float = 3.5,
        on_pause: Optional[Callable[[dict, float], None]] = None,
    ) -> bool:
        """Send raster chunks with FunnyPrint flow control (LOST packet rewind, PAUSE, and FINISHED event)."""
        async with self.lock:
            self.log(f"Starting print job ({len(chunks)} chunks)...")

            # Prepare chunks with blank feed lines
            all_chunks = list(chunks)
            if feed_after > 0:
                blank = bytes(96)
                for _ in range(max(1, feed_after // 2)):
                    all_chunks.append(blank)

            total_lines = len(all_chunks)

            # Discover and connect
            device = await BleakScanner.find_device_by_address(self.mac, timeout=6.0)
            target = device or self.mac

            client = BleakClient(target, timeout=12.0)
            try:
                await client.connect()
                if not client.is_connected:
                    self.log("Failed to connect to printer.")
                    return False

                # Allow BlueZ service discovery to settle
                await asyncio.sleep(0.4)

                # Flush queues
                while not self.ctrl_queue.empty():
                    self.ctrl_queue.get_nowait()
                while not self.hs_queue.empty():
                    self.hs_queue.get_nowait()

                auth_ok = await self._connect_and_auth(client)
                if not auth_ok:
                    self.log("Authentication handshake failed.")
                    return False

                # Set darkness density
                await client.write_gatt_char(WRITE_UUID, pkt_density(density), response=False)
                await asyncio.sleep(0.2)

                # Start session
                await client.write_gatt_char(
                    WRITE_UUID, pkt_print_event(total_lines, end=False), response=False
                )
                await asyncio.sleep(0.1)

                cur_line = 0
                wait_for_finish_cnt = 0
                max_wait_time = max(30, total_lines * 0.4)
                is_finished = False

                while not is_finished:
                    # Check flow control events from printer
                    while not self.ctrl_queue.empty():
                        event_type, val = self.ctrl_queue.get_nowait()
                        if event_type == "lost":
                            # Retransmit from lost_line - 1
                            new_cur = max(0, val - 1)
                            self.log(f"FlowControl: Buffer full, rewinding from line {cur_line} back to {new_cur}")
                            cur_line = new_cur
                            wait_for_finish_cnt = 0
                            await asyncio.sleep(0.2)
                        elif event_type == "pause":
                            self.log("FlowControl: Printer paused, waiting for buffer cooldown...")
                            await asyncio.sleep(0.8)
                        elif event_type == "done":
                            self.log("FlowControl: Printer signaled completion!")
                            is_finished = True
                            break

                    if is_finished:
                        break

                    # Send next raster line
                    if cur_line < total_lines:
                        pkt = pkt_print_line(cur_line, all_chunks[cur_line])
                        await client.write_gatt_char(WRITE_UUID, pkt, response=False)
                        cur_line += 1

                        # Check scheduled pause point for cooling
                        pause_info = None
                        if pause_chunks:
                            for p in pause_chunks:
                                p_chunk = p["chunk"] if isinstance(p, dict) else p
                                if cur_line == p_chunk:
                                    pause_info = p if isinstance(p, dict) else {"chunk": p}
                                    break

                        if pause_info is not None:
                            self.log(f"Print Pacing: Cooling pause for {pause_duration}s at line {cur_line}...")
                            if on_pause:
                                on_pause(pause_info, pause_duration)
                            await asyncio.sleep(pause_duration)
                        else:
                            if on_progress and cur_line % 5 == 0:
                                on_progress(cur_line, total_lines)
                            await asyncio.sleep(0.025)

                    # All lines dispatched, wait for printer to physically finish
                    elif cur_line >= total_lines:
                        if not self.ctrl_queue.empty():
                            event_type, val = self.ctrl_queue.get_nowait()
                            if event_type == "lost":
                                cur_line = max(0, val - 1)
                                wait_for_finish_cnt = 0
                                continue
                            elif event_type == "done":
                                self.log("FlowControl: Printer signaled completion after dispatch!")
                                is_finished = True
                                break

                        wait_for_finish_cnt += 1
                        if wait_for_finish_cnt > int(max_wait_time * 5):
                            self.log("Timeout waiting for printer completion signal, concluding.")
                            break
                        await asyncio.sleep(0.2)


                # Conclude session
                await asyncio.sleep(0.3)
                await client.write_gatt_char(
                    WRITE_UUID, pkt_print_event(total_lines, end=True), response=False
                )
                self.log("Print session completed successfully.")
                await asyncio.sleep(1.5)
                return True

            except Exception as e:
                self.log(f"Print error: {e}")
                return False
            finally:
                if client.is_connected:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
