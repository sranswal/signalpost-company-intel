
from __future__ import annotations

import ctypes
import math
import sys
from collections import Counter
from typing import Iterable

try:
    import resource
except ImportError:
    resource = None


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between zero and one")
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def latency_summary(values: Iterable[float]) -> dict[str, float | int | None]:
    measured = list(values)
    return {
        "n": len(measured),
        "p50_ms": round(percentile(measured, 0.50), 3) if measured else None,
        "p95_ms": round(percentile(measured, 0.95), 3) if measured else None,
        "max_ms": round(max(measured), 3) if measured else None,
    }


def domain_request_summary(counts: Counter[str]) -> dict[str, float | int | None]:
    values = list(counts.values())
    return {
        "domains": len(values),
        "p50_requests": percentile(values, 0.50),
        "p95_requests": percentile(values, 0.95),
        "max_requests": max(values) if values else None,
    }


def peak_rss_bytes() -> int:
    """Return peak resident working-set memory in bytes."""
    if sys.platform == "win32":
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)

        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

        process = kernel32.GetCurrentProcess()
        success = psapi.GetProcessMemoryInfo(
            process,
            ctypes.byref(counters),
            counters.cb,
        )

        if not success:
            raise ctypes.WinError(ctypes.get_last_error())

        return int(counters.PeakWorkingSetSize)

    if resource is None:
        raise RuntimeError("Peak RSS measurement is unsupported on this platform")

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # macOS reports bytes; Linux and most BSD-derived CI images report KiB.
    return int(value if sys.platform == "darwin" else value * 1024)
