import threading
import queue
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None  # type: ignore


@dataclass
class MotorState:
    connected: bool = False
    port: str = "/dev/ttyACM0"
    baud: int = 115200
    posSteps: int = 0
    posMm: float = 0.0
    moving: bool = False
    last_line: str = ""
    last_error: str = ""
    last_update_ts: float = 0.0


class MotorSerialManager:
    """Threaded serial manager for Arduino TB6600 controller.

    - Keeps the serial port open for the life of the Flask app.
    - One writer thread sends commands from a queue.
    - One reader thread parses incoming lines and updates MotorState.
    """

    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 115200, timeout: float = 0.1):
        self.state = MotorState(port=port, baud=baud)
        self._timeout = timeout
        self._ser = None
        self._tx: "queue.Queue[str]" = queue.Queue()
        self._stop = threading.Event()
        self._reader_t: Optional[threading.Thread] = None
        self._writer_t: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if serial is None:
            self.state.last_error = "pyserial not installed"
            return
        try:
            self._ser = serial.Serial(self.state.port, self.state.baud, timeout=self._timeout)
            # Allow Arduino to reboot on serial open
            time.sleep(2.0)
            self.state.connected = True
            self.state.last_error = ""
        except Exception as e:
            self.state.connected = False
            self.state.last_error = f"Serial open failed: {e}"
            return

        self._reader_t = threading.Thread(target=self._read_loop, daemon=True)
        self._writer_t = threading.Thread(target=self._write_loop, daemon=True)
        self._reader_t.start()
        self._writer_t.start()

    def close(self) -> None:
        self._stop.set()
        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass
        self.state.connected = False

    def send(self, cmd: str) -> None:
        """Queue a single-line command (newline auto-appended)."""
        if not cmd.endswith("\n"):
            cmd += "\n"
        self._tx.put(cmd)

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self.state)

    # ---------------- internal loops ----------------
    def _write_loop(self) -> None:
        while not self._stop.is_set():
            try:
                cmd = self._tx.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if self._ser:
                    self._ser.write(cmd.encode("utf-8", errors="ignore"))
            except Exception as e:
                with self._lock:
                    self.state.last_error = f"Serial write failed: {e}"
                    self.state.connected = False
                time.sleep(0.5)

    def _read_loop(self) -> None:
        buf = ""
        while not self._stop.is_set():
            try:
                if not self._ser:
                    time.sleep(0.2)
                    continue
                data = self._ser.read(256)
                if not data:
                    continue
                buf += data.decode("utf-8", errors="ignore")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._handle_line(line)
            except Exception as e:
                with self._lock:
                    self.state.last_error = f"Serial read failed: {e}"
                    self.state.connected = False
                time.sleep(0.5)

    def _handle_line(self, line: str) -> None:
        now = time.time()
        with self._lock:
            self.state.last_line = line
            self.state.last_update_ts = now

        # Parse STATE posSteps=... posMm=... moving=...
        if line.startswith("STATE"):
            parts = line.split()
            kv = {}
            for p in parts[1:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    kv[k] = v
            with self._lock:
                try:
                    if "posSteps" in kv:
                        self.state.posSteps = int(float(kv["posSteps"]))
                    if "posMm" in kv:
                        self.state.posMm = float(kv["posMm"])
                    if "moving" in kv:
                        self.state.moving = str(kv["moving"]).strip() in ("1", "true", "True")
                except Exception:
                    # Keep last good values
                    pass
        elif line.startswith("OK MOVING"):
            with self._lock:
                self.state.moving = True
