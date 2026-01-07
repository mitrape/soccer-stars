# client/udp_peer.py
import socket
import threading
import time
import queue
from typing import Optional, Tuple, Dict, Any, List

from shared.netcodec import dumps_line, loads_line

Addr = Tuple[str, int]


class UDPPeer:
    def __init__(self, local_port: int):
        self.local_port = int(local_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.local_port))
        self.sock.setblocking(False)

        self.running = False
        self._listen_thread: Optional[threading.Thread] = None
        self._hello_thread: Optional[threading.Thread] = None
        self._reliable_thread: Optional[threading.Thread] = None

        self.match_id: Optional[str] = None
        self.peer_addr: Optional[Addr] = None
        self.my_username: Optional[str] = None

        self.connected: bool = False
        self.status_text: str = "Idle"

        self._seq: int = 0
        self.inbox: "queue.Queue[Dict[str, Any]]" = queue.Queue()

        self._pending: Dict[int, Dict[str, Any]] = {}  # seq -> {msg, next_send, tries}
        self._received_shots: set[int] = set()

    def start(self):
        if self.running:
            return
        self.running = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
        self._reliable_thread = threading.Thread(target=self._reliable_loop, daemon=True)
        self._reliable_thread.start()

    def stop(self):
        # ✅ clean stop for ESC exit
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
        self._received_shots.clear()
        self._pending.clear()

        self.start()
        self._start_hello_loop()

    def poll(self) -> List[Dict[str, Any]]:
        msgs: List[Dict[str, Any]] = []
        while True:
            try:
                msgs.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return msgs

    # ---------------- SHOT reliable-ish ----------------
    def send_shot(self, piece_id: int, angle: float, power: float) -> int:
        self._seq += 1
        seq = self._seq
        msg = {
            "type": "SHOT",
            "match_id": self.match_id,
            "seq": seq,
            "piece": int(piece_id),
            "angle": float(angle),
            "power": float(power),
            "t": time.time(),
        }
        self._send(msg)
        self._pending[seq] = {"msg": msg, "next_send": time.time() + 0.08, "tries": 0}
        return seq

    def _reliable_loop(self):
        while self.running:
            now = time.time()
            to_delete = []
            for seq, info in list(self._pending.items()):
                if now >= info["next_send"]:
                    if info["tries"] >= 6:
                        to_delete.append(seq)
                        continue
                    self._send(info["msg"])
                    info["tries"] += 1
                    info["next_send"] = now + 0.12
            for seq in to_delete:
                self._pending.pop(seq, None)
            time.sleep(0.01)

    # ---------------- Phase 7 best-effort ----------------
    def send_state_hash(self, tick: int, hash_str: str):
        self._send({"type": "STATE_HASH", "match_id": self.match_id, "tick": int(tick), "hash": str(hash_str)})

    def send_snapshot_req(self, tick: int):
        self._send({"type": "SNAPSHOT_REQ", "match_id": self.match_id, "tick": int(tick)})

    def send_snapshot(self, tick: int, state: dict):
        self._send({"type": "STATE_SNAPSHOT", "match_id": self.match_id, "tick": int(tick), "state": state})

    # ---------------- HELLO handshake ----------------
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
        while self.running and not self.connected:
            if time.time() - start > 8.0:
                self.status_text = "P2P timeout ❌ (no HELLO_ACK)"
                return
            self._send({"type": "HELLO", "match_id": self.match_id, "from": self.my_username, "udp_port": self.local_port})
            time.sleep(0.2)

    # ---------------- low-level ----------------
    def _send(self, msg: Dict[str, Any]):
        if not self.peer_addr:
            return
        try:
            self.sock.sendto(dumps_line(msg), self.peer_addr)
        except Exception:
            # socket might be closed during exit
            pass

    def _listen_loop(self):
        buffer = b""
        while self.running:
            try:
                data, _addr = self.sock.recvfrom(65535)
            except BlockingIOError:
                time.sleep(0.005)
                continue
            except OSError:
                # socket closed during exit
                break
            except Exception:
                time.sleep(0.01)
                continue

            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = loads_line(line)
                if msg is None:
                    continue
                self._handle(msg)

    def _handle(self, msg: Dict[str, Any]):
        if msg.get("match_id") != self.match_id:
            return

        t = msg.get("type")

        if t == "HELLO":
            self.connected = True
            self.status_text = "P2P connected ✅"
            self._send({"type": "HELLO_ACK", "match_id": self.match_id})

        elif t == "HELLO_ACK":
            self.connected = True
            self.status_text = "P2P connected ✅"

        elif t == "SHOT":
            seq = int(msg.get("seq", 0))
            if seq in self._received_shots:
                self._send({"type": "SHOT_ACK", "match_id": self.match_id, "seq": seq})
                return
            self._received_shots.add(seq)
            self._send({"type": "SHOT_ACK", "match_id": self.match_id, "seq": seq})
            self.inbox.put(msg)

        elif t == "SHOT_ACK":
            seq = int(msg.get("seq", 0))
            self._pending.pop(seq, None)

        elif t in ("STATE_HASH", "SNAPSHOT_REQ", "STATE_SNAPSHOT"):
            self.inbox.put(msg)