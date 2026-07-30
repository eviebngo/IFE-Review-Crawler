"""
Launch the IFE ReviewDB dashboard so others on the same office network can reach it.

Binds to 0.0.0.0 (all network interfaces) instead of 127.0.0.1 (this machine only),
so teammates can open  http://<your-office-IP>:5000/  in their browser.

Run:  python serve.py
Stop: Ctrl+C

Notes:
  * Only reachable while this machine is on and this process is running.
  * Windows Firewall must allow inbound TCP 5000 (see add_firewall_rule.ps1).
  * No login — anyone on the network with the link can use it.
"""
import socket

import app

PORT = 5000


def _lan_ips():
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith(("127.", "169.254.")):
                ips.add(ip)
    except Exception:
        pass
    # Fallback: open a dummy UDP socket to discover the primary outbound IP.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return sorted(ips)


if __name__ == "__main__":
    ips = _lan_ips()
    print("=" * 60)
    print("  IFE ReviewDB — shareable on your office network")
    print("=" * 60)
    if ips:
        print("  Share one of these links with teammates on the same network:")
        for ip in ips:
            print(f"    http://{ip}:{PORT}/?tab=Dashboard")
    else:
        print("  Could not detect your LAN IP — run `ipconfig` and use your")
        print(f"  IPv4 Address like  http://<that-ip>:{PORT}/?tab=Dashboard")
    print("  (This machine also: http://127.0.0.1:%d/ )" % PORT)
    print("  Press Ctrl+C to stop sharing.")
    print("=" * 60)
    app.app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
