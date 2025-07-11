# coding=utf-8
import shutil
import pytest
import os
from persistqueue import PriorityQueue, Empty


@pytest.fixture(autouse=True)
def queue_path(tmp_path):
    path = str(tmp_path / 'priorityqueue')
    yield path
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


class TestPriorityQueue:
    @pytest.fixture(autouse=True)
    def setup_queue(self, queue_path):
        self.queue = PriorityQueue(queue_path)

    def test_put_get_priority(self):
        self.queue.put('low', priority=10)
        self.queue.put('high', priority=1)
        self.queue.put('mid', priority=5)
        assert self.queue.qsize() == 3
        assert self.queue.get() == 'high'
        assert self.queue.get() == 'mid'
        assert self.queue.get() == 'low'
        assert self.queue.empty()
        with pytest.raises(Empty):
            self.queue.get(block=False)

    def test_put_nowait(self):
        self.queue.put_nowait('a', priority=2)
        assert self.queue.get() == 'a'

    def test_empty(self):
        assert self.queue.empty()
        self.queue.put('x', priority=3)
        assert not self.queue.empty()
        self.queue.get()
        assert self.queue.empty()

    def test_qsize(self):
        assert self.queue.qsize() == 0
        self.queue.put('a', priority=1)
        self.queue.put('b', priority=2)
        assert self.queue.qsize() == 2
        self.queue.get()
        assert self.queue.qsize() == 1
        self.queue.get()
        assert self.queue.qsize() == 0
