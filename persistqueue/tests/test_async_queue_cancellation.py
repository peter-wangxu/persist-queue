"""Cancellation must not corrupt subsequent successful queue appends."""
import asyncio
import concurrent.futures
import functools
import threading

import pytest

from persistqueue import AsyncQueue, Queue


class PausingExecutor(concurrent.futures.ThreadPoolExecutor):
    """Pause the return of one real aiofiles executor operation."""

    def __init__(self, loop):
        super().__init__(max_workers=2)
        self.loop = loop
        self.method = None
        self.skip = 0
        self.reached = asyncio.Event()
        self.release = threading.Event()

    def submit(self, fn, *args, **kwargs):
        inner = fn.func if isinstance(fn, functools.partial) else fn
        if self.method and getattr(inner, '__name__', '') == self.method:
            if self.skip:
                self.skip -= 1
                return super().submit(fn, *args, **kwargs)
            self.method = None

            def delayed():
                result = fn(*args, **kwargs)
                self.loop.call_soon_threadsafe(self.reached.set)
                if not self.release.wait(5):
                    raise RuntimeError('test did not release executor')
                return result

            return super().submit(delayed)
        return super().submit(fn, *args, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize('method,chunksize,skip', [
    ('write', 2, 0), ('flush', 2, 0), ('tell', 2, 0),
    ('close', 2, 0), ('replace', 2, 0), ('open', 2, 0),
    ('write', 100, 0), ('flush', 100, 0), ('tell', 100, 0),
    ('replace', 100, 0), ('open', 100, 0), ('write', 100, 1),
])
async def test_cancelled_append_preserves_later_job(
        tmp_path, method, chunksize, skip):
    loop = asyncio.get_running_loop()
    executor = PausingExecutor(loop)
    loop.set_default_executor(executor)
    queue = AsyncQueue(str(tmp_path), chunksize=chunksize)
    jobs = []
    try:
        await queue.put('accepted-before')
        executor.method = method
        executor.skip = skip
        cancelled = asyncio.create_task(queue.put('cancelled-middle'))
        jobs.append(cancelled)
        await asyncio.wait_for(executor.reached.wait(), 2)
        cancelled.cancel()
        await asyncio.sleep(0)
        later = asyncio.create_task(queue.put('accepted-after'))
        jobs.append(later)
        executor.release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(cancelled, 2)
        await asyncio.wait_for(later, 2)
        assert queue.unfinished_tasks == 3
        await queue.close()

        # An independent synchronous reader verifies the persisted format,
        # including cleanup at the chunk boundary after acknowledging items.
        reader = Queue(str(tmp_path))
        try:
            output = []
            while not reader.empty():
                output.append(reader.get_nowait())
                reader.task_done()
            assert output == [
                'accepted-before', 'cancelled-middle', 'accepted-after'
            ]
        finally:
            reader.headf.close()
            reader.tailf.close()
    finally:
        executor.release.set()
        for job in jobs:
            if not job.done():
                job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        await queue.close()


@pytest.mark.asyncio
async def test_repeated_cancellation_retains_writer_lock(tmp_path):
    loop = asyncio.get_running_loop()
    executor = PausingExecutor(loop)
    loop.set_default_executor(executor)
    queue = AsyncQueue(str(tmp_path))
    jobs = []
    try:
        await queue.put('before')
        executor.method = 'flush'
        cancelled = asyncio.create_task(queue.put('middle'))
        jobs.append(cancelled)
        await asyncio.wait_for(executor.reached.wait(), 2)
        for _ in range(3):
            cancelled.cancel()
            await asyncio.sleep(0)
        later = asyncio.create_task(queue.put('after'))
        jobs.append(later)
        await asyncio.sleep(0)
        assert not cancelled.done()
        assert not later.done()
        executor.release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(cancelled, 2)
        await asyncio.wait_for(later, 2)
        assert [await queue.get_nowait() for _ in range(3)] == [
            'before', 'middle', 'after'
        ]
        for _ in range(3):
            await queue.task_done()
        await asyncio.wait_for(queue.join(), 2)
    finally:
        executor.release.set()
        for job in jobs:
            if not job.done():
                job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        await queue.close()


@pytest.mark.asyncio
async def test_cancel_while_waiting_for_capacity(tmp_path):
    async with AsyncQueue(str(tmp_path), maxsize=1) as queue:
        await queue.put('before')
        blocked = asyncio.create_task(queue.put('never-enqueued'))
        await asyncio.sleep(0)
        blocked.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(blocked, 2)
        assert await queue.qsize() == 1
        assert await queue.get_nowait() == 'before'
        await queue.task_done()
        await asyncio.wait_for(queue.join(), 2)


@pytest.mark.asyncio
async def test_cancel_first_put_during_initialization(tmp_path):
    loop = asyncio.get_running_loop()
    executor = PausingExecutor(loop)
    loop.set_default_executor(executor)
    queue = AsyncQueue(str(tmp_path))
    jobs = []
    try:
        executor.method = 'open'
        cancelled = asyncio.create_task(queue.put('never-enqueued'))
        jobs.append(cancelled)
        await asyncio.wait_for(executor.reached.wait(), 2)
        cancelled.cancel()
        executor.release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(cancelled, 2)
        await queue.put('accepted-after')
        assert await queue.get_nowait() == 'accepted-after'
        await queue.task_done()
        await asyncio.wait_for(queue.join(), 2)
    finally:
        executor.release.set()
        for job in jobs:
            if not job.done():
                job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        await queue.close()


@pytest.mark.asyncio
async def test_owned_operation_errors_are_not_suppressed():
    from persistqueue.async_queue import _finish_before_cancelling

    async def fails():
        raise OSError('storage error')

    with pytest.raises(OSError, match='storage error'):
        await _finish_before_cancelling(fails())

    async def cancels_itself():
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(
            _finish_before_cancelling(cancels_itself()), 2
        )


@pytest.mark.asyncio
async def test_cancelled_put_wakes_waiting_consumer(tmp_path):
    loop = asyncio.get_running_loop()
    executor = PausingExecutor(loop)
    loop.set_default_executor(executor)
    queue = AsyncQueue(str(tmp_path))
    jobs = []
    try:
        await queue.qsize()
        consumer = asyncio.create_task(queue.get())
        jobs.append(consumer)
        await asyncio.sleep(0)
        executor.method = 'replace'
        producer = asyncio.create_task(queue.put('committed'))
        jobs.append(producer)
        await asyncio.wait_for(executor.reached.wait(), 2)
        producer.cancel()
        executor.release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(producer, 2)
        assert await asyncio.wait_for(consumer, 2) == 'committed'
        await queue.task_done()
        await asyncio.wait_for(queue.join(), 2)
    finally:
        executor.release.set()
        for job in jobs:
            if not job.done():
                job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        await queue.close()


@pytest.mark.asyncio
async def test_storage_error_after_caller_cancellation_is_reported():
    from persistqueue.async_queue import _finish_before_cancelling

    started = asyncio.Event()
    finish = asyncio.Event()

    async def fails():
        started.set()
        await finish.wait()
        raise OSError('storage error after cancellation')

    owner = asyncio.create_task(_finish_before_cancelling(fails()))
    await asyncio.wait_for(started.wait(), 2)
    owner.cancel()
    await asyncio.sleep(0)
    assert not owner.done()
    finish.set()
    with pytest.raises(OSError, match='storage error after cancellation'):
        await asyncio.wait_for(owner, 2)
