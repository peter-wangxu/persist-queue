# coding=utf-8

import os
import pickle
import random
import shutil
import sys
import pytest
from collections import namedtuple
from threading import Thread

from persistqueue.serializers import json as serializers_json
from persistqueue.serializers import pickle as serializers_pickle
from persistqueue.serializers import msgpack as serializers_msgpack
from persistqueue.serializers import cbor2 as serializers_cbor2

from persistqueue import Queue, Empty, Full

# map keys as params for readable errors from pytest
serializer_params = [
    pytest.param({}, id="serializer=default"),
    pytest.param({"serializer": serializers_json}, id="serializer=json"),
    pytest.param({"serializer": serializers_msgpack}, id="serializer=msgpack"),
    pytest.param({"serializer": serializers_cbor2}, id="serializer=cbor2"),
    pytest.param({"serializer": serializers_pickle}, id="serializer=pickle"),
]


@pytest.fixture(autouse=True)
def queue_path(tmp_path):
    path = str(tmp_path / 'queue')
    yield path
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


class TestPersist:
    @pytest.mark.parametrize("serializer", serializer_params)
    def test_open_close_single(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        q.put('var1')
        del q
        q = Queue(queue_path, **serializer)
        assert q.qsize() == 1
        assert q.get() == 'var1'
        q.task_done()
        del q

    def test_empty(self, queue_path):
        q = Queue(queue_path)
        assert q.empty() is True
        q.put('var1')
        assert q.empty() is False
        q.get()
        assert q.empty() is True

    def test_full(self, queue_path):
        q = Queue(queue_path, maxsize=3)
        for i in range(1, q.maxsize):
            q.put('var{}'.format(i))
        assert q.full() is False
        q.put('var{}'.format(q.maxsize))
        assert q.full() is True
        q.get()
        assert q.full() is False

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_open_close_1000(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        for i in range(1000):
            q.put('var%d' % i)
        assert q.qsize() == 1000
        del q
        q = Queue(queue_path, **serializer)
        assert q.qsize() == 1000
        for i in range(1000):
            data = q.get()
            assert data == 'var%d' % i
            q.task_done()
        with pytest.raises(Empty):
            q.get_nowait()
        q.put('foobar')
        data = q.get()

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_partial_write(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        for i in range(100):
            q.put('var%d' % i)
        del q
        with open(os.path.join(queue_path, 'q00000'), 'ab') as f:
            pickle.dump('文字化け', f)
        q = Queue(queue_path, **serializer)
        assert q.qsize() == 100
        for i in range(100):
            assert q.get() == 'var%d' % i
            q.task_done()
        with pytest.raises(Empty):
            q.get_nowait()

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_random_read_write(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        n = 0
        for i in range(1000):
            if random.random() < 0.5:
                if n > 0:
                    q.get_nowait()
                    q.task_done()
                    n -= 1
                else:
                    with pytest.raises(Empty):
                        q.get_nowait()
            else:
                q.put('var%d' % random.getrandbits(16))
                n += 1

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_multi_threaded(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)

        def producer():
            for i in range(1000):
                q.put('var%d' % i)

        def consumer():
            for i in range(1000):
                q.get()
                q.task_done()
        c = Thread(target=consumer)
        c.start()
        p = Thread(target=producer)
        p.start()
        c.join()
        p.join()
        q.join()
        with pytest.raises(Empty):
            q.get_nowait()

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_garbage_on_head(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        q.put('var1')
        del q
        with open(os.path.join(queue_path, 'q00000'), 'ab') as f:
            f.write(b'garbage')
        q = Queue(queue_path, **serializer)
        q.put('var2')
        assert q.qsize() == 2
        assert q.get() == 'var1'
        q.task_done()

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_task_done_too_many_times(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        q.put('var1')
        q.get()
        q.task_done()
        with pytest.raises(ValueError):
            q.task_done()

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_get_timeout_negative(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        q.put('var1')
        with pytest.raises(ValueError):
            q.get(timeout=-1)

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_get_timeout(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        q.put('var1')
        q.get()
        with pytest.raises(Empty):
            q.get(timeout=1)

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_put_nowait(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        q.put_nowait('var1')
        assert q.get() == 'var1'
        q.task_done()

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_put_maxsize_reached(self, queue_path, serializer):
        q = Queue(queue_path, maxsize=10, **serializer)
        for x in range(10):
            q.put(x)
        with pytest.raises(Full):
            q.put('full_now', block=False)

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_put_timeout_reached(self, queue_path, serializer):
        q = Queue(queue_path, maxsize=2, **serializer)
        for x in range(2):
            q.put(x)
        with pytest.raises(Full):
            q.put('full_and_timeout', block=True, timeout=1)

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_put_timeout_negative(self, queue_path, serializer):
        q = Queue(queue_path, maxsize=1, **serializer)
        with pytest.raises(ValueError):
            q.put('var1', timeout=-1)

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_put_block_and_wait(self, queue_path, serializer):
        q = Queue(queue_path, maxsize=10, **serializer)

        def consumer():
            for i in range(5):
                q.get()
                q.task_done()

        def producer():
            for j in range(16):
                q.put('var%d' % j)
        p = Thread(target=producer)
        p.start()
        c = Thread(target=consumer)
        c.start()
        c.join()
        val = q.get_nowait()
        p.join()
        assert val == 'var5'

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_clear_tail_file(self, queue_path, serializer):
        q = Queue(queue_path, chunksize=10, **serializer)
        for i in range(35):
            q.put('var%d' % i)
        for _ in range(15):
            q.get()
        q = Queue(queue_path, chunksize=10, **serializer)
        assert q.qsize() == 35
        for _ in range(15):
            q.get()
        q.task_done()
        for _ in range(16):
            q.get()
        q.task_done()
        assert q.qsize() == 4

    def test_protocol(self, queue_path):
        expect_protocol = 2 if sys.version_info[0] == 2 else 4
        assert serializers_pickle.protocol == expect_protocol
        serializer = namedtuple("Serializer", ["dump", "load"])(
            serializers_pickle.dump, lambda fp: fp.read())
        q = Queue(path=queue_path, serializer=serializer)
        q.put(b'a')
        assert q.get() == pickle.dumps(b'a', protocol=expect_protocol)

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_del(self, queue_path, serializer):
        q = Queue(queue_path, **serializer)
        q.__del__()
        assert q.headf.closed
        assert q.tailf.closed

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_autosave_get(self, queue_path, serializer):
        q = Queue(queue_path, autosave=True, **serializer)
        q.put('var1')
        q.put('var2')
        assert q.get() == 'var1'
        del q
        q = Queue(queue_path, autosave=True, **serializer)
        assert q.qsize() == 1
        assert q.get() == 'var2'
        del q

    @pytest.mark.parametrize("serializer", serializer_params)
    def test_autosave_join(self, queue_path, serializer):
        q = Queue(queue_path, autosave=True, **serializer)
        for i in range(10):
            q.put('var%d' % i)

        def consumer():
            for i in range(10):
                q.get()
                q.task_done()
        c = Thread(target=consumer)
        c.start()
        q.join()
        with pytest.raises(Empty):
            q.get_nowait()
