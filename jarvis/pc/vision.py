"""See the screen: screenshot, Windows OCR, foreground app."""
from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

from jarvis.paths import DATA

SKIP_TITLES = (
    "password", "login", "sign in", "bank", "paypal", "2fa", "authenticator",
    "private browsing", "incognito",
)

OCR_PS = r"""
param($ImagePath)
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
  Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($WinRtTask, $ResultType) {
  $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
  $netTask = $asTask.Invoke($null, @($WinRtTask))
  $netTask.Wait(-1) | Out-Null
  $netTask.Result
}
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { return }
$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$result.Text
"""


def last_shot_path() -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    return DATA / "last_screen.png"


def foreground() -> dict:
    info = {"title": "", "app": ""}
    if sys.platform != "win32":
        return info
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        n = user32.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(n)
        user32.GetWindowTextW(hwnd, buf, n)
        info["title"] = (buf.value or "").strip()
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            import psutil

            info["app"] = psutil.Process(pid.value).name()
        except Exception:
            pass
    except Exception:
        pass
    return info


def capture(pc) -> Path:
    dest = last_shot_path()
    pc.screenshot(dest)
    return dest


def ocr(path: Path) -> str:
    path = Path(path)
    if sys.platform != "win32" or not path.is_file():
        return ""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-STA", "-Command", OCR_PS, "-ImagePath", str(path)],
            text=True,
            timeout=25,
            stderr=subprocess.DEVNULL,
        )
        return (out or "").strip()
    except Exception:
        return ""


def sensitive(title: str) -> bool:
    t = (title or "").lower()
    return any(s in t for s in SKIP_TITLES)


def describe(pc) -> str:
    fg = foreground()
    title = fg.get("title") or ""
    app = fg.get("app") or ""
    if sensitive(title):
        return f"You're in {app or 'a window'} — looks private, so I didn't read the screen."
    shot = None
    try:
        shot = capture(pc)
    except Exception as e:
        shot = None
        shot_err = str(e)
    text = ""
    if shot:
        text = ocr(shot)
    windows = ""
    try:
        windows = pc.list_windows()
    except Exception:
        windows = ""
    bits = []
    if app or title:
        bits.append(f"Foreground: {app} — {title}".strip(" —"))
    if windows:
        bits.append(windows)
    if text:
        bits.append("Text on screen:\n" + text[:1800])
    elif shot:
        bits.append(f"Screenshot saved ({shot.name}) but I couldn't read the words.")
    if not bits:
        return "Couldn't see the screen."
    return "\n\n".join(bits)
