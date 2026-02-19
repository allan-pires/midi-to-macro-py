"""Focus a process window (e.g. game) by name."""

import sys


def focus_process_window(process_name: str = 'wwm.exe') -> None:
    """Try to bring a window of the given process to foreground. No-op on non-Windows or on failure."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        PROCESS_QUERY_LIMITED = 0x1000
        found_hwnd = []

        def enum_cb(hwnd, _):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return True
            h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid.value)
            if not h:
                return True
            try:
                name_buf = (ctypes.c_wchar * 260)()
                if kernel32.QueryFullProcessImageNameW(h, 0, ctypes.byref(name_buf), ctypes.byref(ctypes.c_ulong(260))):
                    name = name_buf.value
                    if name and name.lower().endswith(process_name.lower()):
                        found_hwnd.append(hwnd)
            finally:
                kernel32.CloseHandle(h)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        if found_hwnd:
            user32.SetForegroundWindow(found_hwnd[0])
    except Exception:
        pass
