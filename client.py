"""
client.py - A simple TCP client for server.py.

Connects to the server, sends newline-terminated messages, and prints each
reply. Runs interactively by default; pass messages as arguments to send
them and exit (handy for scripting and testing).

Usage:
    python client.py [--host HOST] [--port PORT] [message ...]
"""

import argparse
import logging
import socket
import sys

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 65432
BUFFER_SIZE = 1024
ENCODING = "utf-8"
CONNECT_TIMEOUT = 5.0   # Seconds to wait when connecting
REPLY_TIMEOUT = 10.0    # Seconds to wait for each server reply

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CLIENT] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


class SocketClient:
    """Thin wrapper around a TCP socket that exchanges line-based messages.

    Usable as a context manager so the connection is always closed:

        with SocketClient(host, port) as client:
            print(client.send("hello"))
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self._buffer = ""  # Holds bytes received beyond the current line

    def connect(self) -> None:
        """Open the TCP connection to the server."""
        # create_connection() resolves the host, handles IPv4/IPv6, and
        # applies the timeout to the connect attempt.
        self.sock = socket.create_connection(
            (self.host, self.port), timeout=CONNECT_TIMEOUT
        )
        self.sock.settimeout(REPLY_TIMEOUT)
        logger.info("Connected to %s:%s", self.host, self.port)

    def send(self, message: str) -> str:
        """Send one message and return the server's one-line reply.

        Raises:
            ConnectionError: If not connected or the server closes the link.
            socket.timeout: If the server does not reply in time.
        """
        if self.sock is None:
            raise ConnectionError("Not connected")

        # Newline marks the end of a message for the server's parser.
        self.sock.sendall(f"{message}\n".encode(ENCODING))
        return self._read_line()

    def _read_line(self) -> str:
        """Read from the socket until a full newline-terminated line arrives."""
        while "\n" not in self._buffer:
            data = self.sock.recv(BUFFER_SIZE)
            if not data:
                raise ConnectionError("Server closed the connection")
            self._buffer += data.decode(ENCODING, errors="replace")

        line, self._buffer = self._buffer.split("\n", 1)
        return line

    def close(self) -> None:
        """Close the connection if it is open."""
        if self.sock is not None:
            try:
                # Tell the server we are done sending before closing.
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # Socket may already be disconnected.
            self.sock.close()
            self.sock = None
            logger.info("Connection closed")

    def __enter__(self) -> "SocketClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def interactive_session(client: SocketClient) -> None:
    """Read lines from the user and send them until 'quit' or EOF."""
    print("Type a message and press Enter. Type 'quit' to exit.")
    while True:
        try:
            message = input("> ").strip()
        except EOFError:  # Ctrl+Z / Ctrl+D ends input
            break
        if message.lower() in {"quit", "exit"}:
            break
        if message:
            print(client.send(message))


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Simple TCP socket client")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port")
    parser.add_argument(
        "messages", nargs="*", help="Messages to send (omit for interactive)"
    )
    return parser.parse_args()


def main() -> int:
    """Entry point. Returns a process exit code."""
    args = parse_args()
    try:
        with SocketClient(args.host, args.port) as client:
            if args.messages:
                for message in args.messages:
                    print(client.send(message))
            else:
                interactive_session(client)
    except ConnectionRefusedError:
        logger.error("Connection refused - is the server running on %s:%s?",
                     args.host, args.port)
        return 1
    except socket.timeout:
        logger.error("Timed out talking to %s:%s", args.host, args.port)
        return 1
    except socket.gaierror as exc:
        logger.error("Could not resolve host %r: %s", args.host, exc)
        return 1
    except (ConnectionError, OSError) as exc:
        logger.error("Connection error: %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    return 0


if __name__ == "__main__":
    sys.exit(main())
