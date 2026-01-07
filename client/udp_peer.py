# client/udp_peer.py
import socket
import threading
import time
from typing import Optional, Tuple, Dict, Any

from shared.netcodec import dumps_line, loads_line

Addr = Tuple[str, int]


class UDPPeer:
    """
    Phase 3 UDP handshake:
      - bind UDP local_port
      - when match starts: send HELLO every 0.2s until HELLO_ACK (timeout 8s)
      - accept HELLO too (idempotent) and reply HELLO_ACK
      - filter by match_id to avoid mixing games
    """
    def __init__(self, local_port: int):
        self.local_port = int(local_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.local_port))
        self.sock.setblocking(False)

        self.running = False
        self._listen_thread: Optional[threading.Thread] = None
        self._hello_thread: Optional[threading.Thread] = None

        self.match_id: Optional[str] = None
        self.peer_addr: Optional[Addr] = None
        self.my_username: Optional[str] = None

        self.connected: bool = False
        self.status_text: str = "Idle"
        self._seq: int = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass

    def begin_match(self, match_id: str, peer_ip: str, peer_port: int, my_username: str):
        self.match_id = str(match_id)
        self.peer_addr = (str(peer_ip), int(peer_port))
        self.my_username = str(my_username)

        self.connected = False
        self.status_text = "Connecting… (sending HELLO)"
        self._seq = 0

        self.start()
        self._start_hello_loop()

    def _start_hello_loop(self):
        if self._hello_thread and self._hello_thread.is_alive():
            return
        self._hello_thread = threading.Thread(target=self._hello_loop, daemon=True)
        self._hello_thread.start()

    def _hello_loop(self):
        if not self.peer_addr or not self.match_id or not self.my_username:
            self.status_text = "Missing match info"
            return

        start = time.time()
        timeout_s = 8.0

        while self.running and not self.connected:
            if time.time() - start > timeout_s:
                self.status_text = "P2P timeout ❌ (no HELLO_ACK)"
                return

            self._seq += 1
            self._send({
                "type": "HELLO",
                "match_id": self.match_id,
                "from": self.my_username,
                "seq": self._seq,
                "udp_port": self.local_port,
                "t": time.time(),
            })
            time.sleep(0.2)

    def _send(self, msg: Dict[str, Any]):
        if not self.peer_addr:
            return
        try:
            self.sock.sendto(dumps_line(msg), self.peer_addr)
        except OSError:
            pass

    def _listen_loop(self):
        buffer = b""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
            except BlockingIOError:
                time.sleep(0.005)
                continue
            except OSError:
                time.sleep(0.01)
                continue

            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = loads_line(line)
                if msg is None:
                    continue
                self._handle(msg, addr)

    def _handle(self, msg: Dict[str, Any], addr: Addr):
        if msg.get("match_id") != self.match_id:
            return

        t = msg.get("type")

        if t == "HELLO":
            self.connected = True
            self.status_text = "P2P connected ✅"
            self._send({
                "type": "HELLO_ACK",
                "match_id": self.match_id,
                "from": self.my_username,
                "ack": int(msg.get("seq", 0)),
                "t": time.time(),
            })

        elif t == "HELLO_ACK":
            self.connected = True
            self.status_text = "P2P connected ✅"