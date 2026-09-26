"""The flow bar: a small black pill at the bottom of the screen while you dictate.

Drawn with Pillow (anti-aliased, soft shadow) and shown as a per-pixel-alpha
layered window via UpdateLayeredWindow, so the rounded edges are smooth over any
background. The window never takes focus (WS_EX_NOACTIVATE), so the text still
goes to the app you were typing in. Runs on its own thread with a tiny Win32
message loop.
"""

import ctypes
import math
import threading
import time
from ctypes import wintypes

from PIL import Image, ImageDraw, ImageFilter, ImageFont

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

WS_POPUP = 0x80000000
WS_EX_LAYERED, WS_EX_TOPMOST, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE, WS_EX_TRANSPARENT = (
    0x80000, 0x8, 0x80, 0x08000000, 0x20)
ULW_ALPHA = 2
SW_HIDE, SW_SHOWNOACTIVATE = 0, 4
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
# 64-bit handles must not be squeezed through ctypes' default 32-bit int
_H = ctypes.c_void_p
user32.CreateWindowExW.restype = _H
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, _H, _H, _H, _H]
user32.GetDC.restype = _H
user32.GetDC.argtypes = [_H]
user32.ReleaseDC.argtypes = [_H, _H]
user32.ShowWindow.argtypes = [_H, ctypes.c_int]
user32.SetWindowPos.argtypes = [_H, _H, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.UpdateLayeredWindow.argtypes = [_H, _H, ctypes.c_void_p, ctypes.c_void_p, _H, ctypes.c_void_p,
                                       wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
user32.GetDpiForWindow.argtypes = [_H]
kernel32.GetModuleHandleW.restype = _H
gdi32.CreateCompatibleDC.restype = _H
gdi32.CreateCompatibleDC.argtypes = [_H]
gdi32.CreateDIBSection.restype = _H
gdi32.CreateDIBSection.argtypes = [_H, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p, _H, wintypes.DWORD]
gdi32.SelectObject.restype = _H
gdi32.SelectObject.argtypes = [_H, _H]
gdi32.DeleteObject.argtypes = [_H]
gdi32.DeleteDC.argtypes = [_H]


class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


def _font(size, bold=False):
    for name in (["segoeuisb.ttf", "seguisb.ttf"] if bold else []) + ["segoeui.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


class FlowBar:
    BARS = 14

    def __init__(self, get_state):
        """get_state() -> dict(recording, busy, level, preview, latched, idle_bar)"""
        self.get_state = get_state
        self.visible = False
        self.levels = [0.0] * self.BARS
        self.scale = 1.0
        self.hwnd = None
        self.cur = None
        self.idle_drawn = False
        self._cache = {}
        threading.Thread(target=self._run, daemon=True).start()

    # ----- window
    def _run(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self._proc = WNDPROC(lambda h, m, w, l: user32.DefWindowProcW(h, m, w, l))
        wc = WNDCLASS()
        wc.lpfnWndProc = self._proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "SpeakOnFlowBar"
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT,
            "SpeakOnFlowBar", "SpeakOn mic", WS_POPUP, 0, 0, 10, 10, None, None, wc.hInstance, None)
        dpi = user32.GetDpiForWindow(self.hwnd) if hasattr(user32, "GetDpiForWindow") else 96
        self.scale = max(1.0, dpi / 96)
        self.font = _font(int(13 * self.scale))
        k = self.scale
        self.max_w = int(560 * k)
        self.margin = int(16 * k)
        self.canvas = (self.max_w + 2 * self.margin, int(46 * k) + 2 * self.margin)
        msg = wintypes.MSG()
        while True:
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            try:
                self._frame()
            except Exception:
                pass
            time.sleep(1 / 30)

    def _frame(self):
        s = self.get_state()
        active = s["recording"] or s["busy"]
        if not active and not s.get("idle_bar"):
            if self.visible:
                user32.ShowWindow(self.hwnd, SW_HIDE)
                self.visible = False
                self.cur = None
            return
        lv = min(1.0, s["level"] * 12) if s["recording"] else 0.0
        self.levels = self.levels[1:] + [lv]
        target = self._target(s)
        if self.cur is None:
            self.cur = list(target) if not active else [target[0] * 0.3, target[1] * 0.6]
        settled = abs(self.cur[0] - target[0]) < 0.5 and abs(self.cur[1] - target[1]) < 0.5
        if settled and not active and self.idle_drawn:
            return                                  # resting pill already on screen
        self.cur = [c + (t - c) * 0.35 for c, t in zip(self.cur, target)]
        self._blit(self._draw(s, active))
        self.idle_drawn = not active and settled
        if not self.visible:
            user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
            self.visible = True

    # ----- drawing
    def _text(self, s):
        text = " ".join((s.get("preview") or "").split())
        busy = s["busy"] and not s["recording"]
        if len(text) > 64:
            text = "…" + text[-62:]
        if not text:
            text = "Writing…" if busy else "Listening…"
        return text

    def _target(self, s):
        k = self.scale
        if not (s["recording"] or s["busy"]):
            return (46 * k, 10 * k)                  # the resting pill
        text_w = self.font.getlength(self._text(s))
        return (min(self.max_w, 8 * k + 32 * k + 12 * k + (self.BARS * 5 - 2) * k + 14 * k + text_w + 18 * k), 46 * k)

    def _mic(self, d, cx, cy, u, color):
        """mic glyph centred at (cx, cy); u = unit size in pixels"""
        d.rounded_rectangle((cx - 2.6 * u, cy - 5.6 * u, cx + 2.6 * u, cy + 1.6 * u), radius=2.6 * u, fill=color)
        d.arc((cx - 4.6 * u, cy - 4.2 * u, cx + 4.6 * u, cy + 4.0 * u), start=15, end=165, fill=color, width=max(1, int(1.3 * u)))
        d.line((cx, cy + 4.0 * u, cx, cy + 6.2 * u), fill=color, width=max(1, int(1.3 * u)))

    def _draw(self, s, active):
        k = self.scale
        ss = 2
        W, H = self.canvas
        w, h = self.cur
        x0, y1 = (W - w) / 2, H - self.margin
        y0 = y1 - h
        full = active and abs(w - self._target(s)[0]) < 12 * k
        badge = None
        if full:
            if s["busy"] and not s["recording"]:
                badge = (91, 69, 255, 255)
            else:
                pulse = round(2 + 2 * math.sin(time.time() * 5)) / 4 if s.get("latched") else 1.0
                badge = (255, 69, 58, int(170 + 85 * pulse))
        # the shape, shadow and badge are expensive (blur + supersampling): cache them per size
        key = (int(w), int(h), active, badge)
        img = self._cache.get(key)
        if img is None:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            if active:
                sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 4 * k, x0 + w, y1 + 4 * k), radius=h / 2,
                                                     fill=(0, 0, 0, 80))
                img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7 * k)))
            big = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
            d = ImageDraw.Draw(big)
            fill = (18, 18, 20, 245) if active else (18, 18, 20, 150)
            d.rounded_rectangle((x0 * ss, y0 * ss, (x0 + w) * ss, y1 * ss), radius=h * ss / 2, fill=fill,
                                outline=(255, 255, 255, 40 if active else 70), width=ss)
            if badge:
                cy = (y0 + h / 2) * ss
                bx = (x0 + 8 * k + 16 * k) * ss
                r = 15 * k * ss
                d.ellipse((bx - r, cy - r, bx + r, cy + r), fill=badge)
                self._mic(d, bx, cy, 1.55 * k * ss, (255, 255, 255, 255))
            img.alpha_composite(big.resize((W, H), Image.LANCZOS))
            if len(self._cache) > 60:
                self._cache.clear()
            self._cache[key] = img
        img = img.copy()
        if full:
            d = ImageDraw.Draw(img)
            mid = y0 + h / 2
            x = x0 + 8 * k + 32 * k + 12 * k
            busy = s["busy"] and not s["recording"]
            t = time.time()
            for i, lv in enumerate(self.levels):
                if busy:
                    lv = 0.25 + 0.25 * math.sin(t * 8 - i * 0.6)
                bh = max(3 * k, (3 + lv * 20) * k)
                d.rounded_rectangle((x, mid - bh / 2, x + 3 * k, mid + bh / 2), radius=1.5 * k,
                                    fill=(255, 255, 255, 240 if not busy else 150))
                x += 5 * k
            d.text((x + 12 * k, mid), self._text(s), font=self.font, fill=(255, 255, 255, 235), anchor="lm")
        return img

    def _blit(self, img):
        W, H = img.size
        # work area (above the taskbar), bottom centre
        area = wintypes.RECT()
        user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0)
        x = area.left + (area.right - area.left - W) // 2
        y = area.bottom - H - int(6 * self.scale)
        # premultiplied BGRA
        r, g, b, a = img.split()
        from PIL import ImageChops
        r, g, b = (ImageChops.multiply(c, a) for c in (r, g, b))
        data = Image.merge("RGBA", (b, g, r, a)).tobytes()
        hdc_screen = user32.GetDC(None)
        hdc = gdi32.CreateCompatibleDC(hdc_screen)
        bmi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), W, -H, 1, 32, 0, 0, 0, 0, 0, 0)
        bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        ctypes.memmove(bits, data, len(data))
        old = gdi32.SelectObject(hdc, hbmp)
        size = wintypes.SIZE(W, H)
        src = wintypes.POINT(0, 0)
        dst = wintypes.POINT(x, y)
        blend = BLENDFUNCTION(0, 0, 255, 1)
        user32.UpdateLayeredWindow(self.hwnd, hdc_screen, ctypes.byref(dst), ctypes.byref(size), hdc,
                                   ctypes.byref(src), 0, ctypes.byref(blend), ULW_ALPHA)
        user32.SetWindowPos(self.hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # topmost, no move/size/activate
        gdi32.SelectObject(hdc, old)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
        user32.ReleaseDC(None, hdc_screen)
