"""Safe single-instance lock for the Unraid fan-control daemon."""

import fcntl
import os
import stat


def acquire_instance_lock(lock_file):
    """Acquire an exclusive non-blocking lock without truncating a busy file.

    Returns the open file object when acquired, or None if another instance
    holds the lock. Raises OSError for unsafe or inaccessible lock paths.
    """
    flags = os.O_CREAT | os.O_RDWR
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_file, flags, 0o600)

    try:
        file_stat = os.fstat(fd)
        if not stat.S_ISREG(file_stat.st_mode):
            raise OSError("daemon lock path is not a regular file")
        if file_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise OSError("daemon lock file is group/world writable")

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return None

        stream = os.fdopen(fd, "r+", encoding="ascii")
        fd = -1
        stream.seek(0)
        stream.truncate()
        stream.write("%d\n" % os.getpid())
        stream.flush()
        return stream
    finally:
        if fd >= 0:
            os.close(fd)
