import ctypes
import platform
import random
import threading
import time


# =========================
# Windows API
# =========================

if platform.system() != "Windows":
    raise RuntimeError("该连点器仅支持 Windows 系统")

user32 = ctypes.WinDLL("user32", use_last_error=True)

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000

VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B

KEY_MAP = {
    "F1": VK_F1, "F2": VK_F2, "F3": VK_F3, "F4": VK_F4,
    "F5": VK_F5, "F6": VK_F6, "F7": VK_F7, "F8": VK_F8,
    "F9": VK_F9, "F10": VK_F10, "F11": VK_F11, "F12": VK_F12,
}

DEFAULT_HOTKEYS = {
    "start":   {"name": "F6", "vk": VK_F6},
    "pause":   {"name": "F7", "vk": VK_F7},
    "capture": {"name": "F8", "vk": VK_F8},
    "stop":    {"name": "F9", "vk": VK_F9},
}


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long)
    ]


user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = ctypes.c_bool

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = ctypes.c_bool

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

user32.mouse_event.argtypes = [
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong
]
user32.mouse_event.restype = None


def get_cursor_position():
    point = POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return point.x, point.y


def set_cursor_position(x, y):
    ok = user32.SetCursorPos(int(x), int(y))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())


def mouse_click(button="left"):
    if button == "left":
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    elif button == "right":
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    else:
        raise ValueError("button 只能是 left 或 right")


def mouse_click_at(x, y, button="left"):
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    norm_x = int(x * 65535 / max(screen_w, 1))
    norm_y = int(y * 65535 / max(screen_h, 1))
    abs_flags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
    user32.mouse_event(abs_flags, norm_x, norm_y, 0, 0)
    time.sleep(0.005)
    if button == "left":
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    elif button == "right":
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

def is_key_pressed(vk_code):
    return user32.GetAsyncKeyState(vk_code) & 0x8000 != 0


# =========================
# 连点器引擎
# =========================

class AutoClickerEngine:
    def __init__(self):
        self._running = False
        self._paused = False
        self._stop_event = threading.Event()
        self._click_thread = None
        self._settings = None
        self._lock = threading.RLock()

        self.on_status = None
        self.on_stopped = None

    @property
    def state(self):
        with self._lock:
            if not self._running:
                return "idle"
            if self._paused:
                return "paused"
            return "running"

    def start(self, settings):
        with self._lock:
            if self._running:
                return False

            self._settings = dict(settings)
            self._paused = False
            self._stop_event.clear()
            self._running = True

            self._click_thread = threading.Thread(
                target=self._click_loop,
                daemon=True
            )
            self._click_thread.start()

        self._emit_status("状态：运行中")
        return True

    def pause(self):
        with self._lock:
            if not self._running or self._paused:
                return False

            self._paused = True

        self._emit_status("状态：已暂停")
        return True

    def resume(self):
        with self._lock:
            if not self._running or not self._paused:
                return False

            self._paused = False

        self._emit_status("状态：运行中")
        return True

    def reconfigure(self, settings):
        with self._lock:
            if self._running:
                self._settings = dict(settings)

    def stop(self, wait=True):
        with self._lock:
            self._running = False
            self._paused = False
            self._stop_event.set()
            thread = self._click_thread

        if (
            wait
            and thread
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=2.0)

    def _click_loop(self):
        clicked = 0

        with self._lock:
            settings = dict(self._settings or {})

        try:
            interval = float(settings.get("interval", 0.1))
            count = int(settings.get("count", 0))
            button = settings.get("button", "left")
            mode = settings.get("mode", "fixed" if settings.get("use_fixed_position") else "cursor")
            fx = int(settings.get("x", 0))
            fy = int(settings.get("y", 0))
            rx = int(settings.get("range_x", 0))
            ry = int(settings.get("range_y", 0))
            rw = int(settings.get("range_w", 100))
            rh = int(settings.get("range_h", 100))

            while True:
                with self._lock:
                    running = self._running
                    paused = self._paused

                if not running or self._stop_event.is_set():
                    break

                if count != 0 and clicked >= count:
                    break

                if paused:
                    if self._stop_event.wait(timeout=0.05):
                        break
                    with self._lock:
                        s = self._settings or {}
                        interval = float(s.get("interval", 0.1))
                        count = int(s.get("count", 0))
                        button = s.get("button", "left")
                        mode = s.get("mode", "cursor")
                        fx = int(s.get("x", 0))
                        fy = int(s.get("y", 0))
                        rx = int(s.get("range_x", 0))
                        ry = int(s.get("range_y", 0))
                        rw = int(s.get("range_w", 100))
                        rh = int(s.get("range_h", 100))
                    continue

                if mode == "fixed":
                    mouse_click_at(fx, fy, button)
                elif mode == "range":
                    cx = rx + (random.randint(0, rw - 1) if rw > 0 else 0)
                    cy = ry + (random.randint(0, rh - 1) if rh > 0 else 0)
                    mouse_click_at(cx, cy, button)
                else:
                    mouse_click(button)
                clicked += 1

                self._emit_status(f"状态：运行中，已点击 {clicked} 次")

                if self._wait_interval(interval):
                    break

        finally:
            with self._lock:
                self._running = False
                self._paused = False
                self._stop_event.set()

            self._emit_status("状态：已停止")
            self._emit_stopped()

    def _wait_interval(self, seconds):
        if seconds <= 0:
            return self._stop_event.is_set()

        end_time = time.monotonic() + seconds

        while True:
            if self._stop_event.is_set():
                return True

            with self._lock:
                if not self._running or self._paused:
                    return False

            remaining = end_time - time.monotonic()
            if remaining <= 0:
                return False

            if self._stop_event.wait(timeout=min(remaining, 0.05)):
                return True

    def _emit_status(self, message):
        callback = self.on_status
        if callback:
            try:
                callback(message)
            except Exception:
                pass

    def _emit_stopped(self):
        callback = self.on_stopped
        if callback:
            try:
                callback()
            except Exception:
                pass