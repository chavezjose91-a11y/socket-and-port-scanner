"""
server.py - A simple TCP echo server.

Listens for incoming client connections, receives newline-terminated
messages, and sends back an acknowledgement for each one. Each client is
handled in its own thread so several clients can be connected at once.

Usage:
    python server.py [--host HOST] [--port PORT]
"""

import argparse
import logging
import socket
import threading

# Default network settings. 127.0.0.1 keeps the server reachable only from
# this machine; use 0.0.0.0 to accept connections from other hosts.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 65432
BUFFER_SIZE = 1024          # Max bytes read per recv() call
ENCODING = "utf-8"
CLIENT_TIMEOUT = 60.0       # Seconds of client inactivity before disconnect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SERVER] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def handle_client(conn: socket.socket, addr: tuple) -> None:
    """Serve a single connected client until it disconnects.

    Args:
        conn: The socket object for this client connection.
        addr: The (host, port) tuple of the client.
    """
    logger.info("Connection established with %s:%s", *addr)
    conn.settimeout(CLIENT_TIMEOUT)

    # `with` guarantees the client socket is closed, even on error.
    with conn:
        buffer = ""
        try:
            while True:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    # An empty read means the client closed the connection.
                    logger.info("Client %s:%s disconnected", *addr)
                    break

                # TCP is a byte stream, not a message stream: one recv() may
                # contain part of a message or several messages. Buffer the
                # data and split on newlines to recover whole messages.
                buffer += data.decode(ENCODING, errors="replace")
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    message = message.strip()
                    if not message:
                        continue

                    logger.info("Received from %s:%s -> %r", *addr, message)
                    reply = f"Server received: {message}\n"
                    # sendall() keeps sending until every byte is written.
                    conn.sendall(reply.encode(ENCODING))

        except socket.timeout:
            logger.warning("Client %s:%s timed out", *addr)
        except ConnectionResetError:
            logger.warning("Client %s:%s reset the connection", *addr)
        except OSError as exc:
            logger.error("Socket error with %s:%s: %s", *addr, exc)


def run_server(host: str, port: int) -> None:
    """Create the listening socket and accept clients forever.

    Args:
        host: Interface address to bind to.
        port: TCP port to listen on.
    """
    # AF_INET = IPv4, SOCK_STREAM = TCP.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        # Allow quick restarts without "Address already in use" errors
        # while the old socket lingers in TIME_WAIT.
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            server_sock.bind((host, port))
        except OSError as exc:
            logger.error("Could not bind to %s:%s: %s", host, port, exc)
            raise SystemExit(1) from exc

        # Allow up to 5 pending connections in the backlog queue.
        server_sock.listen(5)
        # A timeout on accept() lets Ctrl+C be noticed promptly on Windows,
        # where a blocking accept() would otherwise ignore KeyboardInterrupt.
        server_sock.settimeout(1.0)
        logger.info("Listening on %s:%s (Ctrl+C to stop)", host, port)

        try:
            while True:
                try:
                    conn, addr = server_sock.accept()
                except socket.timeout:
                    continue  # No new client yet; loop to check for Ctrl+C.

                # Accepted sockets inherit the listener's timeout; reset it
                # so handle_client can apply its own.
                conn.settimeout(None)
                # Daemon threads won't block interpreter exit on shutdown.
                thread = threading.Thread(
                    target=handle_client, args=(conn, addr), daemon=True
                )
                thread.start()
        except KeyboardInterrupt:
            logger.info("Shutdown requested, closing server")


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Simple TCP socket server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_server(args.host, args.port)
