"""
port_scanner.py - A simple multithreaded TCP port scanner.

For each port in a range, it tries a full TCP connection (a "connect scan")
and reports which ports accept it. Connections are opened and closed straight
away, and no data is sent.

Only scan hosts you own or have written permission to test. For this
assignment, the scanner refuses any target except this computer
(localhost / 127.x.x.x) and scanme.nmap.org, which the Nmap project provides
for testing scanners.

Usage:
    python port_scanner.py [target] [-p PORTS] [-t TIMEOUT] [-w WORKERS]
                           [-d DELAY] [--show-closed]

Examples:
    python port_scanner.py                              # localhost, 1-1024
    python port_scanner.py 127.0.0.1 -p 21,22,80,443 -t 2.5 --show-closed
    python port_scanner.py scanme.nmap.org -p 22,80,443 -w 2 -d 1
"""

import argparse
import errno
import ipaddress
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime

DEFAULT_TARGET = "127.0.0.1"
DEFAULT_PORTS = "1-1024"
DEFAULT_TIMEOUT = 0.5       # Seconds to wait for each connection attempt
DEFAULT_WORKERS = 100       # Most ports scanned at the same time
DEFAULT_DELAY = 0.01        # Seconds between starting connection attempts
MIN_PORT, MAX_PORT = 1, 65535

# Host names this scanner is allowed to scan. Loopback addresses
# (127.0.0.0/8 and ::1) are always allowed as well.
AUTHORIZED_HOSTS = {"localhost", "scanme.nmap.org"}

# Error codes from connect_ex() that mean "a host answered and refused" (the
# port is closed), as opposed to timeouts or unreachable networks. Windows uses
# WSAECONNREFUSED (10061), so check both.
REFUSED_CODES = {errno.ECONNREFUSED, getattr(errno, "WSAECONNREFUSED", 10061)}


@dataclass(frozen=True)
class PortResult:
    """Outcome of scanning a single port."""
    port: int
    state: str              # "open", "closed" or "filtered"
    service: str = ""       # Well-known service name, if any


def timestamp() -> str:
    """Current local date and time, for the scan log."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_ports(spec: str) -> list[int]:
    """Turn a port spec like "22,80,8000-8100" into a sorted list of ports.

    Raises:
        ValueError: If the spec is malformed or a port is out of range.
    """
    ports: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                start_str, end_str = part.split("-", 1)
                start, end = int(start_str), int(end_str)
            else:
                start = end = int(part)
        except ValueError:
            raise ValueError(f"not a number: {part!r}") from None

        if start > end:
            raise ValueError(f"range start is above its end: {part}")
        if not (MIN_PORT <= start <= MAX_PORT and MIN_PORT <= end <= MAX_PORT):
            raise ValueError(f"ports must be between {MIN_PORT} and {MAX_PORT}: {part}")
        ports.update(range(start, end + 1))

    if not ports:
        raise ValueError("no ports given")
    return sorted(ports)


def is_authorized(target: str, ip: str) -> bool:
    """Return True if the target is one we are allowed to scan."""
    if target.lower() in AUTHORIZED_HOSTS:
        return True
    # Any loopback address (this computer) is fine, e.g. 127.0.0.1.
    return ipaddress.ip_address(ip).is_loopback


def service_name(port: int) -> str:
    """Look up the well-known service for a TCP port, or return ""."""
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return ""


def scan_port(ip: str, port: int, timeout: float) -> PortResult:
    """Try one TCP connection and classify the port.

    - open:     the connection was accepted
    - closed:   the host refused it (it sent a TCP reset)
    - filtered: no answer in time, or another network error, which usually
                means a firewall dropped the packets

    Note: on Windows a refused connection is only reported after about 2
    seconds, because Windows retries the connection first. With a shorter
    timeout, closed ports show as "filtered". Use -t 2.5 or more on Windows
    to tell closed and filtered ports apart.
    """
    # `with` makes sure the socket is closed whatever happens.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            # connect_ex() returns an error code instead of raising, which
            # makes it easy to tell refused ports from unanswered ones.
            code = sock.connect_ex((ip, port))
        except OSError:  # includes socket.timeout
            return PortResult(port, "filtered")

    if code == 0:
        return PortResult(port, "open", service_name(port))
    if code in REFUSED_CODES:
        return PortResult(port, "closed")
    return PortResult(port, "filtered")


def scan(ip: str, ports: list[int], timeout: float, workers: int,
         delay: float) -> list[PortResult]:
    """Scan ports at the same time using a thread pool.

    Scanning is network-bound (threads spend their time waiting for replies),
    so threads speed it up a lot despite Python's GIL. To stay polite, at
    most `workers` connections are open at once, and a new attempt starts at
    most once every `delay` seconds.
    """
    results: list[PortResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        for port in ports:
            futures.append(pool.submit(scan_port, ip, port, timeout))
            if delay:
                time.sleep(delay)  # Rate limit: space out connection attempts
        for done, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            # Progress line, overwritten in place on stderr.
            print(f"\rScanned {done}/{len(ports)} ports", end="", file=sys.stderr)
    print(file=sys.stderr)
    return sorted(results, key=lambda r: r.port)


def print_report(target: str, ip: str, results: list[PortResult],
                 started: str, elapsed: float, show_closed: bool) -> None:
    """Print a readable summary of the scan."""
    open_ports = [r for r in results if r.state == "open"]
    shown = results if show_closed else open_ports
    closed = sum(r.state == "closed" for r in results)
    filtered = len(results) - len(open_ports) - closed

    print(f"\nScan report for {target} ({ip})")
    print(f"Started:  {started}")
    print(f"Finished: {timestamp()}")
    rate = len(results) / elapsed if elapsed else 0
    print(f"Scanned {len(results)} ports in {elapsed:.2f} seconds "
          f"({rate:.0f} ports/second)\n")

    if shown:
        print(f"{'PORT':<10}{'STATE':<10}SERVICE")
        for r in shown:
            print(f"{str(r.port) + '/tcp':<10}{r.state:<10}{r.service}")
    else:
        print("No open ports found.")

    print(f"\n{len(open_ports)} open, {closed} closed, {filtered} filtered")
    if filtered == len(results):
        print("Warning: no port answered. The host may be down, unreachable, "
              "or behind a firewall.\n(On Windows, closed ports also look like "
              "this unless the timeout is 2.5 seconds or more.)")


def parse_args() -> argparse.Namespace:
    """Parse and check command-line options."""
    parser = argparse.ArgumentParser(
        description="Multithreaded TCP connect port scanner. Only scans "
                    "localhost and scanme.nmap.org."
    )
    parser.add_argument("target", nargs="?", default=DEFAULT_TARGET,
                        help=f"Host name or IP to scan (default {DEFAULT_TARGET})")
    parser.add_argument("-p", "--ports", default=DEFAULT_PORTS,
                        help=f'Ports, e.g. "80", "1-1024", "22,80,8000-8100" '
                             f"(default {DEFAULT_PORTS})")
    parser.add_argument("-t", "--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"Seconds per connection attempt (default {DEFAULT_TIMEOUT})")
    parser.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Most ports scanned at once (default {DEFAULT_WORKERS})")
    parser.add_argument("-d", "--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Seconds between connection attempts (default {DEFAULT_DELAY})")
    parser.add_argument("--show-closed", action="store_true",
                        help="List closed and filtered ports too")
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("timeout must be greater than 0")
    if not 1 <= args.workers <= 500:
        parser.error("workers must be between 1 and 500")
    if args.delay < 0:
        parser.error("delay cannot be negative")
    try:
        args.port_list = parse_ports(args.ports)
    except ValueError as exc:
        parser.error(f"invalid port list {args.ports!r}: {exc}")
    return args


def main() -> int:
    """Entry point. Returns a process exit code."""
    args = parse_args()

    # Resolve the host name first; an unknown or unreachable name fails here.
    try:
        ip = socket.gethostbyname(args.target)
    except (socket.gaierror, UnicodeError) as exc:
        print(f"Error: could not resolve host {args.target!r}: {exc}", file=sys.stderr)
        return 1

    if not is_authorized(args.target, ip):
        print(f"Error: {args.target} ({ip}) is not an authorized target. "
              f"Only localhost and scanme.nmap.org may be scanned.", file=sys.stderr)
        return 2

    started = timestamp()
    print(f"[{started}] Scanning {args.target} ({ip}): {len(args.port_list)} ports, "
          f"timeout {args.timeout}s, {args.workers} workers, delay {args.delay}s",
          file=sys.stderr)
    start = time.perf_counter()
    try:
        results = scan(ip, args.port_list, args.timeout, args.workers, args.delay)
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Scan cancelled by user.", file=sys.stderr)
        return 130
    elapsed = time.perf_counter() - start

    print_report(args.target, ip, results, started, elapsed, args.show_closed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
