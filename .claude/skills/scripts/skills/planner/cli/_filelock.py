"""Cross-platform exclusive file lock — drop-in replacement for the
`fcntl.flock(fd, fcntl.LOCK_EX)` subset used by qr.py and qr_commands.py.

POSIX:   delegates to fcntl.flock (advisory).
Windows: msvcrt.locking(fd, LK_LOCK, 1) on byte 0 of the file.
         LK_LOCK retries 10x at 1s intervals and then raises; the inner
         while loop makes the wait unbounded so semantics match flock.

Why this shim and not e.g. portalocker:
- One call pattern across two files — full library is overkill.
- Standard library only — keeps the planner skill dependency-free.
"""
from __future__ import annotations

import os
import sys


if sys.platform == "win32":
    import msvcrt

    LOCK_EX = 2  # sentinel; mirrors fcntl.LOCK_EX so the call sites unchanged

    def flock(fd: int, op: int) -> None:
        # Lock byte 0; all participants lock the same byte so writes serialize.
        # The qr_commands writers never mutate the original file in place
        # (tempfile + os.rename), so locking byte 0 does not collide with writes.
        pos = os.lseek(fd, 0, 1)
        try:
            os.lseek(fd, 0, 0)
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
                    return
                except OSError:
                    continue
        finally:
            os.lseek(fd, pos, 0)
else:
    import fcntl as _fcntl

    LOCK_EX = _fcntl.LOCK_EX

    def flock(fd: int, op: int) -> None:
        _fcntl.flock(fd, op)
