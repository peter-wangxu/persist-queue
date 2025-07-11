"""Asynchronous persistent queue API.

This module provides asynchronous interfaces compatible with existing
synchronous APIs. Since file I/O is inherently asynchronous, these async
versions can better utilize asynchronous programming models.
"""
import asyncio
import logging
import os
import tempfile
from time import time as _time
from typing import Any, Optional, Tuple
import aiofiles
import aiofiles.os

from persistqueue.exceptions import Empty, Full
import persistqueue.serializers.pickle

log = logging.getLogger(__name__)


async def _truncate_async(fn: str, length: int) -> None:
    """Asynchronously truncate file to specified length."""
    async with aiofiles.open(fn, 'ab+') as f:
        await f.truncate(length)


async def atomic_rename_async(src: str, dst: str) -> None:
    """Asynchronously atomically rename file."""
    await aiofiles.os.replace(src, dst)


class AsyncQueue:
    """Asynchronous thread-safe persistent queue."""

    def __init__(
        self,
        path: str,
        maxsize: int = 0,
        chunksize: int = 100,
        tempdir: Optional[str] = None,
        serializer: Any = persistqueue.serializers.pickle,
        autosave: bool = False
    ) -> None:
        """Create an asynchronous persistent queue object.

        Args:
            path: Directory path where queue data is stored
            maxsize: Maximum queue size, 0 means unlimited
            chunksize: Number of entries in each chunk file
            tempdir: Temporary file directory
            serializer: Serializer object
            autosave: Whether to auto-save
        """
        log.debug('Initializing async file queue with path {}'.format(
            path))
        self.path = path
        self.chunksize = chunksize
        self.tempdir = tempdir
        self.maxsize = maxsize
        self.serializer = serializer
        self.autosave = autosave
        self._init(maxsize)

        if self.tempdir:
            if os.stat(self.path).st_dev != os.stat(self.tempdir).st_dev:
                raise ValueError("tempdir must be located on the same "
                                 "filesystem as queue path")
        else:
            fd, tempdir = tempfile.mkstemp()
            if os.stat(self.path).st_dev != os.stat(tempdir).st_dev:
                self.tempdir = self.path
                log.warning("Default tempdir '%(dft_dir)s' is not on the "
                            "same filesystem with queue path '%(queue_path)s'"
                            ", defaulting to '%(new_path)s'." % {
                               "dft_dir": tempdir,
                               "queue_path": self.path,
                               "new_path": self.tempdir})
            os.close(fd)
            os.remove(tempdir)

        # These will be set during async initialization
        self.info = None
        self.headf = None
        self.tailf = None
        self.unfinished_tasks = 0
        self.update_info = True
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self._all_tasks_done = asyncio.Condition(self._lock)

    def _init(self, maxsize: int) -> None:
        """Initialize queue internal state."""
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    async def _async_init(self) -> None:
        """Asynchronously initialize queue."""
        if self.info is None:
            self.info = await self._loadinfo()
            # Truncate garbage data in head file
            hnum, hcnt, hoffset = self.info['head']
            headfn = self._qfile(hnum)
            if os.path.exists(headfn):
                if hoffset < os.path.getsize(headfn):
                    await _truncate_async(headfn, hoffset)
            # Open head file
            self.headf = await self._openchunk_async(hnum, 'ab+')
            tnum, _, toffset = self.info['tail']
            self.tailf = await self._openchunk_async(tnum)
            await self.tailf.seek(toffset)
            # Update unfinished tasks count
            self.unfinished_tasks = self.info['size']

    async def join(self) -> None:
        """Wait for all tasks to complete."""
        async with self._all_tasks_done:
            while self.unfinished_tasks:
                await self._all_tasks_done.wait()

    async def qsize(self) -> int:
        """Return queue size."""
        async with self._lock:
            await self._async_init()
            return self._qsize()

    def _qsize(self) -> int:
        """Internal method to get queue size."""
        return self.info['size']

    async def empty(self) -> bool:
        """Check if queue is empty."""
        return await self.qsize() == 0

    async def full(self) -> bool:
        """Check if queue is full."""
        return await self.qsize() == self.maxsize

    async def put(self, item: Any, block: bool = True,
                  timeout: Optional[float] = None) -> None:
        """Put item into queue."""
        async with self._not_full:
            await self._async_init()
            if self.maxsize > 0:
                if not block:
                    if self._qsize() == self.maxsize:
                        raise Full
                elif timeout is None:
                    while self._qsize() == self.maxsize:
                        await self._not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    endtime = _time() + timeout
                    while self._qsize() == self.maxsize:
                        remaining = endtime - _time()
                        if remaining <= 0.0:
                            raise Full
                        await asyncio.wait_for(
                            self._not_full.wait(), remaining)
            await self._put(item)
            self.unfinished_tasks += 1
            self._not_empty.notify()

    async def _put(self, item: Any) -> None:
        """Internal put method."""
        # Note: We need to handle synchronous serializer calls here
        # In practice, async serializers may be needed
        self.serializer.dump(item, self.headf)
        await self.headf.flush()
        hnum, hpos, _ = self.info['head']
        hpos += 1
        if hpos == self.info['chunksize']:
            hpos = 0
            hnum += 1
            await self.headf.fsync()
            await self.headf.close()
            self.headf = await self._openchunk_async(hnum, 'ab+')
        self.info['size'] += 1
        self.info['head'] = [hnum, hpos, await self.headf.tell()]
        await self._saveinfo()

    async def put_nowait(self, item: Any) -> None:
        """Non-blocking put."""
        await self.put(item, False)

    async def get(self, block: bool = True,
                  timeout: Optional[float] = None) -> Any:
        """Get item from queue."""
        async with self._not_empty:
            await self._async_init()
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    await self._not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = _time() + timeout
                while not self._qsize():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Empty
                    await asyncio.wait_for(self._not_empty.wait(), remaining)
            item = await self._get()
            self._not_full.notify()
            return item

    async def get_nowait(self) -> Any:
        """Non-blocking get."""
        return await self.get(False)

    async def _get(self) -> Any:
        """Internal get method."""
        tnum, tcnt, toffset = self.info['tail']
        hnum, hcnt, _ = self.info['head']
        if [tnum, tcnt] >= [hnum, hcnt]:
            return None
        # Note: We need to handle synchronous serializer calls here
        data = self.serializer.load(self.tailf)
        toffset = await self.tailf.tell()
        tcnt += 1
        if tcnt == self.info['chunksize'] and tnum <= hnum:
            tcnt = toffset = 0
            tnum += 1
            await self.tailf.close()
            self.tailf = await self._openchunk_async(tnum)
        self.info['size'] -= 1
        self.info['tail'] = [tnum, tcnt, toffset]
        if self.autosave:
            await self._saveinfo()
            self.update_info = False
        else:
            self.update_info = True
        return data

    async def task_done(self) -> None:
        """Mark task as done."""
        async with self._all_tasks_done:
            unfinished = self.unfinished_tasks - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError("task_done() called too many times")
                self._all_tasks_done.notify_all()
            self.unfinished_tasks = unfinished
            await self._task_done()

    async def _task_done(self) -> None:
        """Internal task_done method."""
        if self.autosave:
            return
        if self.update_info:
            await self._saveinfo()
            self.update_info = False

    async def _openchunk_async(
        self, number: int, mode: str = 'rb'
    ) -> aiofiles.threadpool.AsyncBufferedIOBase:
        """Asynchronously open chunk file."""
        return await aiofiles.open(self._qfile(number), mode)

    async def _loadinfo(self) -> dict:
        """Asynchronously load queue info."""
        infopath = self._infopath()
        if os.path.exists(infopath):
            async with aiofiles.open(infopath, 'rb') as f:
                content = await f.read()
                # Note: We need to handle synchronous serializer here
                import io
                info = self.serializer.load(io.BytesIO(content))
        else:
            info = {
                'chunksize': self.chunksize,
                'size': 0,
                'tail': [0, 0, 0],
                'head': [0, 0, 0],
            }
        return info

    async def _gettempfile_async(self) -> Tuple[int, str]:
        """Asynchronously get temporary file."""
        if self.tempdir:
            return tempfile.mkstemp(dir=self.tempdir)
        else:
            return tempfile.mkstemp()

    async def _saveinfo(self) -> None:
        """Asynchronously save queue info."""
        tmpfd, tmpfn = await self._gettempfile_async()
        async with aiofiles.open(tmpfn, "wb") as tmpfo:
            # Note: We need to handle synchronous serializer here
            import io
            buffer = io.BytesIO()
            self.serializer.dump(self.info, buffer)
            await tmpfo.write(buffer.getvalue())
        await atomic_rename_async(tmpfn, self._infopath())
        await self._clear_tail_file()

    async def _clear_tail_file(self) -> None:
        """Asynchronously clear tail files."""
        tnum, _, _ = self.info['tail']
        while tnum >= 1:
            tnum -= 1
            path = self._qfile(tnum)
            if os.path.exists(path):
                await aiofiles.os.remove(path)
            else:
                break

    def _qfile(self, number: int) -> str:
        """Get queue file path."""
        return os.path.join(self.path, 'q%05d' % number)

    def _infopath(self) -> str:
        """Get info file path."""
        return os.path.join(self.path, 'info')

    async def close(self) -> None:
        """Close queue."""
        for to_close in self.headf, self.tailf:
            if to_close and not to_close.closed:
                await to_close.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self._async_init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
