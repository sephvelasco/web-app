import os
import time
import cv2


class USBCamera:
    """V4L2 USB camera wrapper tuned for low-latency preview and ML verification.

    Defaults are conservative for Raspberry Pi stability:
      - MJPEG
      - 640x480
      - 15 FPS
      - minimal buffering
    """

    def __init__(
        self,
        device: str | int = "/dev/video0",
        width: int = 640,
        height: int = 480,
        fps: int = 15,
        use_mjpeg: bool = True,
        warmup_frames: int = 5,
    ):
        self.device = device
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.use_mjpeg = bool(use_mjpeg)
        self.cap = None

        self._open()

        # Warm up (some webcams output junk frames initially)
        for _ in range(max(0, int(warmup_frames))):
            self.read()
            time.sleep(0.02)

    def _open(self):
        # Accept either an int index or a /dev/videoX path
        src = self.device
        if isinstance(src, str) and src.startswith("/dev/video"):
            # OpenCV accepts the path string with CAP_V4L2
            cap = cv2.VideoCapture(src, cv2.CAP_V4L2)
        else:
            cap = cv2.VideoCapture(int(src), cv2.CAP_V4L2)

        if not cap.isOpened():
            raise RuntimeError(f"Failed to open USB camera: {self.device}")

        # Prefer MJPEG to reduce USB bandwidth + CPU load
        if self.use_mjpeg:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Reduce buffering if supported
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self.cap = cap

    def read(self):
        """Return (ret, frame_bgr)."""
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None


def discover_usb_video_device(preferred: str | None = None, max_index: int = 30) -> str | None:
    """Best-effort discovery for a working /dev/videoX node.

    Why: systems with CSI cameras + libcamera can expose many /dev/video* nodes.
    ffplay may be pointed at a node that works, but OpenCV might fail on another.

    Strategy:
      1) If preferred is provided, try it first.
      2) Scan /dev/video0..max_index and return the first node that opens.
    """
    candidates: list[str] = []
    if preferred:
        candidates.append(preferred)

    for i in range(max_index + 1):
        candidates.append(f"/dev/video{i}")

    for dev in candidates:
        if not os.path.exists(dev):
            continue
        try:
            cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap.release()
                continue

            # Some nodes open but don't produce frames; verify we can read.
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                return dev
        except Exception:
            try:
                cap.release()
            except Exception:
                pass
            continue

    return None
