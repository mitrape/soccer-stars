import socket
import threading
import json
import queue

class TcpClient:
    def __init__(self):
        self.sock = None
        self.reader_thread = None
        self.inbox = queue.Queue()
        self.connected = False

    def connect(self, host: str, port: int) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.connected = True
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()
            return True
        except Exception as e:
            self.inbox.put({"type": "ERROR", "message": f"Connect failed: {e}"})
            self.connected = False
            return False

    def _read_loop(self):
        buf = ""
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data.decode(errors="ignore")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except:
                        msg = {"type": "ERROR", "message": "Bad JSON from server"}
                    self.inbox.put(msg)
        except Exception as e:
            self.inbox.put({"type": "ERROR", "message": f"Disconnected: {e}"})
        finally:
            self.connected = False
            try:
                self.sock.close()
            except:
                pass

    def send(self, msg: dict):
        if not self.connected or not self.sock:
            self.inbox.put({"type": "ERROR", "message": "Not connected"})
            return
        try:
            payload = json.dumps(msg) + "\n"
            self.sock.sendall(payload.encode())
        except Exception as e:
            self.inbox.put({"type": "ERROR", "message": f"Send failed: {e}"})
            self.connected = False

    def poll(self):
        """Get all pending messages (non-blocking)."""
        msgs = []
        while True:
            try:
                msgs.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return msgs
