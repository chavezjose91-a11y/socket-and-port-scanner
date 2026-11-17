# Port Scanner: Demonstration and Test Report

**Files:** `port_scanner.py` (the scanner), `scan_tests.ps1` (runs each test case)
**Environment:** Windows 11, Python 3.15.2
**Date:** 2026-11-17

Each test case is run with `.\scan_tests.ps1 <number>`. The script prints a
header with the test name and the time it ran, shows each command, and runs it.
The scanner also prints its own start and finish times, so every screenshot
carries timestamps.

---

## Scope and ethical scanning

Only these targets were scanned, as the assignment allows:

- **This computer:** `127.0.0.1` / `localhost`
- **scanme.nmap.org:** a host the Nmap project provides for testing scanners

The scanner enforces this itself. Before scanning, it checks the target and
refuses anything that isn't a loopback address, `localhost` or
`scanme.nmap.org` (see test case 5).

How the scanner keeps scanning gentle:

| Safeguard | How it works |
|---|---|
| Delay between attempts | `-d` sets the seconds between starting connections (default 0.01 s, at most about 100 attempts per second) |
| Limit on parallel connections | `-w` caps how many connections are open at once (default 100, maximum 500) |
| No data sent | Each connection is opened and closed straight away, with nothing sent |
| Gentle settings for the remote host | scanme.nmap.org was scanned with only 8 ports, 2 workers and 1 s between attempts |

No other host was scanned, and no aggressive or flooding scans were run.
Test case 5 looks up `example.com` only to show that the scanner refuses it.
It does a DNS lookup and makes no connection.

### How ports are classified

| State | Meaning |
|---|---|
| open | The connection was accepted |
| closed | The host answered and refused the connection |
| filtered | No answer before the timeout, which usually means a firewall dropped it |

On Windows, a refused connection is only reported after about 2 seconds,
because Windows retries first. Closed ports therefore look "filtered" with the
default 0.5 s timeout, so the tests that need closed ports use `-t 2.5`.

---

## Test case 1: Common ports on localhost

**Command:** `.\scan_tests.ps1 1`, which runs
`py port_scanner.py 127.0.0.1 -p 21,22,80,443,135,445 -t 2.5 --show-closed`

**Expected:** Each port is reported as open or closed. FTP (21), SSH (22),
HTTP (80) and HTTPS (443) are not running on this PC, so they should be closed.
Windows' own RPC (135) and SMB (445) services should be open.

**Actual output:**
```
=== Test case 1: Common ports on localhost ===
Run at: 2026-11-17 00:24:28

> py port_scanner.py 127.0.0.1 -p 21,22,80,443,135,445 -t 2.5 --show-closed
[2026-11-17 00:24:30] Scanning 127.0.0.1 (127.0.0.1): 6 ports, timeout 2.5s, 100 workers, delay 0.01s

Scan report for 127.0.0.1 (127.0.0.1)
Started:  2026-11-17 00:24:30
Finished: 2026-11-17 00:24:32
Scanned 6 ports in 2.07 seconds (3 ports/second)

PORT      STATE     SERVICE
21/tcp    closed
22/tcp    closed
80/tcp    closed
135/tcp   open      epmap
443/tcp   closed
445/tcp   open      microsoft-ds

2 open, 4 closed, 0 filtered
```

**Result:** PASS. Both open and closed ports were found, and open ports are
labelled with their service name.

![Test 1 - common ports on localhost](screenshots/scan1_common_ports.png)

---

## Test case 2: Custom port range on localhost

**Command:** `.\scan_tests.ps1 2`, which runs
`py port_scanner.py 127.0.0.1 -p 130-145 -t 2.5 --show-closed`

**Expected:** All 16 ports in the range are scanned and classified.

**Actual output:**
```
=== Test case 2: Custom port range on localhost ===
Run at: 2026-11-17 00:24:32

> py port_scanner.py 127.0.0.1 -p 130-145 -t 2.5 --show-closed
Started:  2026-11-17 00:24:33
Finished: 2026-11-17 00:24:35
Scanned 16 ports in 2.20 seconds (7 ports/second)

PORT      STATE     SERVICE
130/tcp   closed
...
134/tcp   closed
135/tcp   open      epmap
136/tcp   closed
137/tcp   filtered
138/tcp   closed
...
145/tcp   closed

1 open, 14 closed, 1 filtered
```

**Result:** PASS. The range showed all three states. Port 137 (NetBIOS) is
"filtered" because Windows Firewall drops it instead of refusing it.

![Test 2 - custom range on localhost](screenshots/scan2_custom_range.png)

---

## Test case 3: Selected ports on scanme.nmap.org

**Command:** `.\scan_tests.ps1 3`, which runs
`py port_scanner.py scanme.nmap.org -p 21,22,23,25,80,443,9929,31337 -t 3 -w 2 -d 1 --show-closed`

**Expected:** A small, slow scan of 8 well-known ports. scanme.nmap.org is
known to run SSH (22), HTTP (80) and an Nping echo service (9929).

**Actual output:**
```
=== Test case 3: Selected ports on scanme.nmap.org ===
Run at: 2026-11-17 00:24:30

> py port_scanner.py scanme.nmap.org -p 21,22,23,25,80,443,9929,31337 -t 3 -w 2 -d 1 --show-closed
[2026-11-17 00:24:30] Scanning scanme.nmap.org (45.33.32.156): 8 ports, timeout 3.0s, 2 workers, delay 1.0s

Scan report for scanme.nmap.org (45.33.32.156)
Started:  2026-11-17 00:24:30
Finished: 2026-11-17 00:24:39
Scanned 8 ports in 9.15 seconds (1 ports/second)

PORT      STATE     SERVICE
21/tcp    closed
22/tcp    open      ssh
23/tcp    closed
25/tcp    closed
80/tcp    open      http
443/tcp   closed
9929/tcp  open
31337/tcp closed

3 open, 5 closed, 0 filtered
```

**Result:** PASS. Ports 22, 80 and 9929 were open, which matches the services
scanme.nmap.org is known to run. The 1 s delay kept the scan to about one
connection per second.

![Test 3 - scanme.nmap.org](screenshots/scan3_scanme.png)

---

## Test case 4: Error handling for invalid port numbers and options

**Command:** `.\scan_tests.ps1 4`

**Expected:** Every bad input is rejected with a clear message and exit code
2, before any scanning starts, and with no Python traceback.

**Actual output:**

| Input | Message | Exit code |
|---|---|---|
| `-p 0` | `invalid port list '0': ports must be between 1 and 65535: 0` | 2 |
| `-p 70000` | `invalid port list '70000': ports must be between 1 and 65535: 70000` | 2 |
| `-p abc` | `invalid port list 'abc': not a number: 'abc'` | 2 |
| `-p 100-50` | `invalid port list '100-50': range start is above its end: 100-50` | 2 |
| `-t 0` | `timeout must be greater than 0` | 2 |
| `-d -1` | `delay cannot be negative` | 2 |

**Result:** PASS

![Test 4 - invalid inputs](screenshots/scan4_invalid_inputs.png)

---

## Test case 5: Error handling for unreachable and unauthorized hosts

**Command:** `.\scan_tests.ps1 5`

**Expected:** A host name that doesn't exist fails cleanly with exit code 1.
A host outside the allowed scope is refused with exit code 2, and no
connection is made to it.

**Actual output:**
```
> py port_scanner.py no-such-host.invalid -p 80
Error: could not resolve host 'no-such-host.invalid': [Errno 11001] getaddrinfo failed
Exit code: 1

> py port_scanner.py example.com -p 80
Error: example.com (104.20.23.154) is not an authorized target. Only localhost and scanme.nmap.org may be scanned.
Exit code: 2
```

**Result:** PASS. If a host resolves but never answers, every port comes back
"filtered" and the scanner warns that the host may be down, unreachable or
behind a firewall. Test case 6 (100 ports) shows this warning.

![Test 5 - unreachable and unauthorized hosts](screenshots/scan5_bad_hosts.png)

---

## Test case 6: Performance with different port ranges

**Command:** `.\scan_tests.ps1 6`. All runs scan `127.0.0.1` with the default
0.5 s timeout.

**Actual results:**

| Run | Ports | Workers | Delay | Time | Ports/second | Open ports found |
|---|---|---|---|---|---|---|
| 1-100 | 100 | 100 | 0.01 s | 1.59 s | 63 | none |
| 1-500 | 500 | 100 | 0.01 s | 5.74 s | 87 | 135, 445 |
| 1-1000 | 1000 | 100 | 0.01 s | 11.01 s | 91 | 135, 445 |
| 1-2000 | 2000 | 100 | 0.01 s | 21.64 s | 92 | 135, 445 |
| 1-1000, no delay | 1000 | 100 | 0 | 5.14 s | 194 | 135, 445 |
| 1-500, 10 workers | 500 | 10 | 0.01 s | 25.39 s | 20 | 135, 445 |

**What the numbers show:**
- **Time grows in line with the number of ports.** At the default settings the
  scanner runs at just over 90 ports per second, which matches the cap set by
  the 0.01 s delay (at most 100 attempts per second).
- **The delay is the main limit.** With no delay, the same 1000 ports took half
  as long. Here the limit is 100 workers each waiting up to 0.5 s, so at most
  200 ports per second.
- **Too few workers slows it down a lot.** With 10 workers, each port with no
  answer ties up a worker for the full 0.5 s timeout, so it drops to about
  20 ports per second (10 ÷ 0.5).
- The 1-100 run found no open ports because 135 and 445 are outside that range.
  It also shows the "no port answered" warning.

**Result:** PASS

![Test 6 - performance, part 1 (1-100 and 1-500)](screenshots/scan6_performance_part1.png)

![Test 6 - performance, part 2 (1-1000 and 1-2000)](screenshots/scan6_performance_part2.png)

![Test 6 - performance, part 3 (no delay, and 10 workers)](screenshots/scan6_performance_part3.png)

---

## Summary

| # | Test case | Target | Result |
|---|---|---|---|
| 1 | Common ports (21, 22, 80, 443, 135, 445) | 127.0.0.1 | PASS |
| 2 | Custom port range (130-145) | 127.0.0.1 | PASS |
| 3 | Selected ports, gentle settings | scanme.nmap.org | PASS |
| 4 | Invalid port numbers and options | none (rejected) | PASS |
| 5 | Unreachable and unauthorized hosts | none (rejected) | PASS |
| 6 | Performance with different ranges | 127.0.0.1 | PASS |

All 6 test cases passed. Only localhost and scanme.nmap.org were scanned.
