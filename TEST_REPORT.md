# Socket Client-Server: Demonstration and Test Report

**Files under test:** `server.py`, `client.py`, `test_no_server.ps1`
**Environment:** Windows 11, Python 3.15.2, server bound to `127.0.0.1:65432`
**Date:** 2026-11-17

The demonstration uses two terminals: **Terminal 1 (server)** and
**Terminal 2 (client)**. A third terminal is used for step 7. Each step lists
what was done, what was expected, the actual output, and its screenshot.
Screenshots go in the `screenshots/` folder under the names shown.

---

## Step 1: Start the server

**Action:** In Terminal 1, run `py server.py`.

**Expected:** The server creates a TCP socket, binds to the port, and logs that
it is listening.

**Actual output (Terminal 1):**
```
> py server.py
2026-11-17 00:13:58,932 [SERVER] INFO: Listening on 127.0.0.1:65432 (Ctrl+C to stop)
```

**Result:** PASS

![Step 1 - server listening](screenshots/step1_server_listening.png)

---

## Step 2: Start the client

**Action:** In Terminal 2, run `py client.py "Hello from the client!"`.

**Expected:** The client connects to the server and logs the connection.
At the same moment the server logs a new connection from the client's address.

**Actual output:**
```
Terminal 2:  2026-11-17 00:14:12,507 [CLIENT] INFO: Connected to 127.0.0.1:65432
Terminal 1:  2026-11-17 00:14:12,508 [SERVER] INFO: Connection established with 127.0.0.1:52910
```

**Result:** PASS

![Step 2 - client connected](screenshots/step2_client_connected.png)

---

## Step 3: Send a test message from the client to the server

**Action:** The same client command sends the message `Hello from the client!`.
The client adds a newline to mark the end of the message and sends it with
`sendall()`.

**Expected:** The message is sent with no error.

**Actual:** The message was sent. The server's log in step 4 shows it arrived.

**Result:** PASS. Covered by the step 2 and step 4 screenshots.

---

## Step 4: Server receives and processes the message

**Action:** Look at Terminal 1.

**Expected:** The server reads the bytes, rebuilds the full message up to the
newline, logs it, and builds a reply.

**Actual output (Terminal 1):**
```
2026-11-17 00:14:12,508 [SERVER] INFO: Received from 127.0.0.1:52910 -> 'Hello from the client!'
```

**Result:** PASS

![Step 4 - server received message](screenshots/step4_server_received.png)

---

## Step 5: Server response reaches the client

**Action:** Look at Terminal 2.

**Expected:** The client prints the server's reply to the message it sent.

**Actual output (Terminal 2):**
```
Server received: Hello from the client!
```

**Result:** PASS

![Step 5 - client got the reply](screenshots/step5_client_response.png)

---

## Step 6: Graceful disconnection

**Action:** The client finishes and closes its connection. Then press Ctrl+C in
Terminal 1 to shut the server down.

**Expected:**
- The client shuts down its socket and logs `Connection closed`.
- The server sees the client leave, logs it, and keeps listening.
- On Ctrl+C the server logs the shutdown, closes its socket, and returns to
  the prompt with no traceback.

**Actual output:**
```
Terminal 2:  2026-11-17 00:14:12,508 [CLIENT] INFO: Connection closed
Terminal 1:  2026-11-17 00:14:12,508 [SERVER] INFO: Client 127.0.0.1:52910 disconnected
Terminal 1:  2026-11-17 00:14:27,622 [SERVER] INFO: Shutdown requested, closing server
```

**Result:** PASS

![Step 6 - client disconnect and server shutdown](screenshots/step6_disconnection.png)

---

## Step 7: Error handling when the server is not running

**Action:** With the server stopped, run `.\test_no_server.ps1` in a new
terminal. It runs `py client.py "Is anyone there?"` and then prints the
client's exit code.

**Expected:** The client catches the refused connection, prints a clear error
with no traceback, and exits with code 1.

**Actual output (Terminal 3):**
```
> py client.py "Is anyone there?"
2026-11-17 00:14:32,837 [CLIENT] ERROR: Connection refused - is the server running on 127.0.0.1:65432?
Exit code: 1
```

**Result:** PASS

![Step 7 - error when server is down](screenshots/step7_server_not_running.png)

---

## Summary

| Step | What it shows                                  | Result |
|------|------------------------------------------------|--------|
| 1    | Server starts and listens                      | PASS   |
| 2    | Client connects                                | PASS   |
| 3    | Client sends a test message                    | PASS   |
| 4    | Server receives and processes the message      | PASS   |
| 5    | Server's reply reaches the client              | PASS   |
| 6    | Graceful disconnection and server shutdown     | PASS   |
| 7    | Error handling when the server is not running  | PASS   |

All 7 steps passed.
