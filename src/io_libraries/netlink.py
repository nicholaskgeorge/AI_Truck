# netlink.py
#
# One class that can send/receive UDP datagrams and framed TCP messages,
# with an application-level CRC32 appended to every message.
#
# Usage model (recommended):
#   - Jetson runs TCP server + UDP receiver
#   - Pi runs TCP client + UDP sender
#
# Notes:
#   - UDP: bad CRC packets are dropped (recv returns None)
#   - TCP: bad CRC messages return None (you may choose to close/reconnect)

import socket
import struct
import zlib
from dataclasses import dataclass
from typing import Optional, Tuple

# TCP framing: 4-byte big-endian length prefix (length includes payload+crc)
_LEN_FMT = "!I"
_LEN_SIZE = struct.calcsize(_LEN_FMT)

_CRC_FMT = "!I"
_CRC_SIZE = struct.calcsize(_CRC_FMT)


@dataclass
class NetLinkConfig:
    # UDP
    udp_bind: Tuple[str, int] = ("0.0.0.0", 5005)      # where we receive UDP
    udp_peer: Optional[Tuple[str, int]] = None         # where we send UDP

    # TCP (choose one mode)
    tcp_listen: Optional[Tuple[str, int]] = None       # server mode if set
    tcp_peer: Optional[Tuple[str, int]] = None         # client mode if set

    # Timeouts
    udp_timeout_s: float = 0.05
    tcp_timeout_s: float = 0.5
    tcp_backlog: int = 1

    # Behavior on CRC failure (TCP only)
    tcp_close_on_bad_crc: bool = True


class NetLink:
    """
    One class providing:
      - UDP send/recv (datagram + CRC32)
      - TCP send/recv (length-framed message + CRC32)

    CRC32 is computed over the payload bytes only, appended as 4 bytes big-endian.
    """

    def __init__(self, cfg: NetLinkConfig):
        self.cfg = cfg

        # UDP socket (always available)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(cfg.udp_bind)
        self.udp_sock.settimeout(cfg.udp_timeout_s)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 16)

        # TCP sockets (optional)
        self.tcp_server_sock: Optional[socket.socket] = None
        self.tcp_sock: Optional[socket.socket] = None  # connected socket

        if cfg.tcp_listen and cfg.tcp_peer:
            raise ValueError("Choose either tcp_listen (server) or tcp_peer (client), not both.")

        if cfg.tcp_listen:
            self._tcp_setup_server(cfg.tcp_listen)

    # ---------------- CRC helpers ----------------

    @staticmethod
    def _crc32(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF

    @classmethod
    def _append_crc(cls, payload: bytes) -> bytes:
        return payload + struct.pack(_CRC_FMT, cls._crc32(payload))

    @classmethod
    def _verify_and_strip_crc(cls, buf: bytes) -> Optional[bytes]:
        if len(buf) < _CRC_SIZE:
            return None
        payload, crc_bytes = buf[:-_CRC_SIZE], buf[-_CRC_SIZE:]
        (want,) = struct.unpack(_CRC_FMT, crc_bytes)
        got = cls._crc32(payload)
        return payload if got == want else None

    # ---------------- UDP ----------------

    def send_udp(self, payload: bytes, peer: Optional[Tuple[str, int]] = None) -> None:
        """
        Send a UDP datagram to 'peer' if provided, else to cfg.udp_peer.
        Appends CRC32 automatically.
        """
        dest = peer or self.cfg.udp_peer
        if dest is None:
            raise ValueError("No UDP peer provided. Set cfg.udp_peer or pass peer=(host,port).")
        self.udp_sock.sendto(self._append_crc(payload), dest)

    def recv_udp(self, max_bytes: int = 2048) -> Optional[Tuple[bytes, Tuple[str, int]]]:
        """
        Receive one UDP datagram. Returns (payload, addr) or None on timeout/bad CRC.
        """
        try:
            data, addr = self.udp_sock.recvfrom(max_bytes)
            payload = self._verify_and_strip_crc(data)
            if payload is None:
                return None  # bad checksum -> drop
            return payload, addr
        except socket.timeout:
            return None

    # ---------------- TCP (framed) ----------------

    def _tcp_setup_server(self, listen_addr: Tuple[str, int]) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(listen_addr)
        s.listen(self.cfg.tcp_backlog)
        s.settimeout(self.cfg.tcp_timeout_s)
        self.tcp_server_sock = s

    def connect_tcp(self) -> None:
        """
        In client mode, connect to cfg.tcp_peer.
        """
        if not self.cfg.tcp_peer:
            raise ValueError("cfg.tcp_peer is not set (not in TCP client mode).")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.cfg.tcp_timeout_s)
        s.connect(self.cfg.tcp_peer)
        s.settimeout(self.cfg.tcp_timeout_s)
        self.tcp_sock = s

    def accept_tcp(self) -> Optional[Tuple[str, int]]:
        """
        In server mode, accept one connection if available.
        Returns client addr or None on timeout.
        """
        if not self.tcp_server_sock:
            raise ValueError("TCP server socket not configured (cfg.tcp_listen is None).")
        try:
            conn, addr = self.tcp_server_sock.accept()
            conn.settimeout(self.cfg.tcp_timeout_s)
            self.tcp_sock = conn
            return addr
        except socket.timeout:
            return None

    def tcp_connected(self) -> bool:
        return self.tcp_sock is not None

    def send_tcp(self, payload: bytes) -> None:
        """
        Send one framed TCP message over the connected TCP socket.
        Adds CRC32 automatically; length includes payload+crc.
        """
        if not self.tcp_sock:
            raise RuntimeError("TCP not connected. Call connect_tcp() or accept_tcp() first.")

        framed_payload = self._append_crc(payload)
        header = struct.pack(_LEN_FMT, len(framed_payload))
        self.tcp_sock.sendall(header + framed_payload)

    def recv_tcp(self) -> Optional[bytes]:
        """
        Receive one framed TCP message.
        Returns payload bytes on success.
        Returns None on timeout, disconnect, or bad CRC.
        If tcp_close_on_bad_crc is True, closes TCP on CRC failure.
        """
        if not self.tcp_sock:
            raise RuntimeError("TCP not connected. Call connect_tcp() or accept_tcp() first.")

        try:
            header = self._recv_exact(_LEN_SIZE)
            if header is None:
                self._close_tcp_only()
                return None

            (n,) = struct.unpack(_LEN_FMT, header)

            if n < _CRC_SIZE:
                # Length too small to even contain CRC -> treat as stream corruption
                if self.cfg.tcp_close_on_bad_crc:
                    self._close_tcp_only()
                return None

            buf = self._recv_exact(n)
            if buf is None:
                self._close_tcp_only()
                return None

            payload = self._verify_and_strip_crc(buf)
            if payload is None and self.cfg.tcp_close_on_bad_crc:
                self._close_tcp_only()
            return payload

        except socket.timeout:
            return None

    def _recv_exact(self, n: int) -> Optional[bytes]:
        """
        Receive exactly n bytes from connected TCP socket.
        Returns None if peer closed.
        """
        assert self.tcp_sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self.tcp_sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    # ---------------- Lifecycle ----------------

    def _close_tcp_only(self) -> None:
        if self.tcp_sock:
            try:
                self.tcp_sock.close()
            except Exception:
                pass
            self.tcp_sock = None

    def close(self) -> None:
        try:
            self.udp_sock.close()
        except Exception:
            pass

        self._close_tcp_only()

        if self.tcp_server_sock:
            try:
                self.tcp_server_sock.close()
            except Exception:
                pass
            self.tcp_server_sock = None