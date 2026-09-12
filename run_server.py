#!/usr/bin/env python3
"""Run script for ZiriZiriDTP Web Server."""

import socket
import uvicorn

def get_local_ip():
    """Find local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    ip = get_local_ip()
    port = 8080
    print("=" * 60)
    print("  🚀 ZiriZiriDTP Web Server Starting!")
    print(f"  📱 Access from smartphone: http://{ip}:{port}")
    print(f"  💻 Access from PC:         http://localhost:{port}")
    print("=" * 60)
    uvicorn.run("ziriziri.server:app", host="0.0.0.0", port=port, reload=True)
