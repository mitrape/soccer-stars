# client/network.py
import socket
import threading
import queue
from typing import Dict, Any, List, Optional

from shared.netcodec import dumps_line, loads_line


class TcpClient:
    def __init__(self):
        self.sock: Optional[socket.socket] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.inbox: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.connected: bool = False
        self._stop = False

    def connect(self, host: str, port: int) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.connected = True
            self._stop = False

            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            return True
        except Exception as e:
            self.inbox.put({"type": "ERROR", "message": f"Connect failed: {e}"})
            self.connected = False
            return False

    def close(self):
        self._stop = True
        self.connected = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None

    def _read_loop(self):
        buf = b""
        try:
            while not self._stop and self.sock:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data

                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = loads_line(line)
                    if msg is None:
                        self.inbox.put({"type": "ERROR", "message": "Bad JSON from server"})
                    else:
                        self.inbox.put(msg)

        except Exception as e:
            self.inbox.put({"type": "ERROR", "message": f"Disconnected: {e}"})
        finally:
            self.connected = False
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass

    def send(self, msg: Dict[str, Any]):
        if not self.connected or not self.sock:
            self.inbox.put({"type": "ERROR", "message": "Not connected"})
            return
        try:
            self.sock.sendall(dumps_line(msg))
        except Exception as e:
            self.inbox.put({"type": "ERROR", "message": f"Send failed: {e}"})
            self.connected = False

    def poll(self) -> List[Dict[str, Any]]:
        msgs: List[Dict[str, Any]] = []
        while True:
            try:
                msgs.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return msgs