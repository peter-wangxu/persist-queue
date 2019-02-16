# coding=utf-8

import os
import pickle
import random
import shutil
import sys
import tempfile
import unittest
from collections import namedtuple
from nose2.tools import params
from threading import Thread

import persistqueue.serializers.json
import persistqueue.serializers.msgpack
import persistqueue.serializers.pickle
from persistqueue import Queue, Empty, Full

# map keys as params for readable errors from nose
serializer_params = {
    "serializer=default": {},
    "serializer=json": {"serializer": persistqueue.serializers.json},
    "serializer=msgpack": {"serializer": persistqueue.serializers.msgpack},
    "serializer=pickle": {"serializer": persistqueue.serializers.pickle},
}


class PersistTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='queue')

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    @params(*serializer_params)
    def test_open_close_single(self, serializer):
        """Write 1 item, close, reopen checking if same item is there"""

        q = Queue(self.path, **serializer_params[serializer])
        q.put('var1')
        del q
        q = Queue(self.path, **serializer_params[serializer])
        self.assertEqual(1, q.qsize())
        self.assertEqual('var1', q.get())
        q.task_done()

    @params(*serializer_params)
    def test_open_close_1000(self, serializer):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = Queue(self.path, **serializer_params[serializer])
        for i in range(1000):
            q.put('var%d' % i)
        self.assertEqual(1000, q.qsize())
        del q
        q = Queue(self.path, **serializer_params[serializer])
        self.assertEqual(1000, q.qsize())
        for i in range(1000):
            data = q.get()
            self.assertEqual('var%d' % i, data)
            q.task_done()
        with self.assertRaises(Empty):
            q.get_nowait()
        # assert adding another one still works
        q.put('foobar')
        data = q.get()

    @params(*serializer_params)
    def test_partial_write(self, serializer):
        """Test recovery from previous crash w/ partial write"""

        q = Queue(self.path, **serializer_params[serializer])
        for i in range(100):
            q.put('var%d' % i)
        del q
        with open(os.path.join(self.path, 'q00000'), 'ab') as f:
            pickle.dump('文字化け', f)
        q = Queue(self.path, **serializer_params[serializer])
        self.assertEqual(100, q.qsize())
        for i in range(100):
            self.assertEqual('var%d' % i, q.get())
            q.task_done()
        with self.assertRaises(Empty):
            q.get_nowait()

    @params(*serializer_params)
    def test_random_read_write(self, serializer):
        """Test random read/write"""

        q = Queue(self.path, **serializer_params[serializer])
        n = 0
        for i in range(1000):
            if random.random() < 0.5:
                if n > 0:
                    q.get_nowait()
                    q.task_done()
                    n -= 1
                else:
                    with self.assertRaises(Empty):
                        q.get_nowait()
            else:
                q.put('var%d' % random.getrandbits(16))
                n += 1

    @params(*serializer_params)
    def test_multi_threaded(self, serializer):
        """Create consumer and producer threads, check parallelism"""

        q = Queue(self.path, **serializer_params[serializer])

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
        with self.assertRaises(Empty):
            q.get_nowait()

    @params(*serializer_params)
    def test_garbage_on_head(self, serializer):
        """Adds garbage to the queue head and let the internal integrity
        checks fix it"""

        q = Queue(self.path, **serializer_params[serializer])
        q.put('var1')
        del q

        with open(os.path.join(self.path, 'q00000'), 'ab') as f:
            f.write(b'garbage')
        q = Queue(self.path, **serializer_params[serializer])
        q.put('var2')

        self.assertEqual(2, q.qsize())
        self.assertEqual('var1', q.get())
        q.task_done()

    @params(*serializer_params)
    def test_task_done_too_many_times(self, serializer):
        """Test too many task_done called."""
        q = Queue(self.path, **serializer_params[serializer])
        q.put('var1')
        q.get()
        q.task_done()

        with self.assertRaises(ValueError):
            q.task_done()

    @params(*serializer_params)
    def test_get_timeout_negative(self, serializer):
        q = Queue(self.path, **serializer_params[serializer])
        q.put('var1')
        with self.assertRaises(ValueError):
            q.get(timeout=-1)

    @params(*serializer_params)
    def test_get_timeout(self, serializer):
        """Test when get failed within timeout."""
        q = Queue(self.path, **serializer_params[serializer])
        q.put('var1')
        q.get()
        with self.assertRaises(Empty):
            q.get(timeout=1)

    @params(*serializer_params)
    def test_put_nowait(self, serializer):
        """Tests the put_nowait interface."""
        q = Queue(self.path, **serializer_params[serializer])
        q.put_nowait('var1')
        self.assertEqual('var1', q.get())
        q.task_done()

    @params(*serializer_params)
    def test_put_maxsize_reached(self, serializer):
        """Test that maxsize reached."""
        q = Queue(self.path, maxsize=10, **serializer_params[serializer])
        for x in range(10):
            q.put(x)

        with self.assertRaises(Full):
            q.put('full_now', block=False)

    @params(*serializer_params)
    def test_put_timeout_reached(self, serializer):
        """Test put with block and timeout."""
        q = Queue(self.path, maxsize=2, **serializer_params[serializer])
        for x in range(2):
            q.put(x)

        with self.assertRaises(Full):
            q.put('full_and_timeout', block=True, timeout=1)

    @params(*serializer_params)
    def test_put_timeout_negative(self, serializer):
        """Test and put with timeout < 0"""
        q = Queue(self.path, maxsize=1, **serializer_params[serializer])
        with self.assertRaises(ValueError):
            q.put('var1', timeout=-1)

    @params(*serializer_params)
    def test_put_block_and_wait(self, serializer):
        """Test block until queue is not full."""
        q = Queue(self.path, maxsize=10, **serializer_params[serializer])

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
        self.assertEqual('var5', val)

    @params(*serializer_params)
    def test_clear_tail_file(self, serializer):
        """Test that only remove tail file when calling task_done."""
        q = Queue(self.path, chunksize=10, **serializer_params[serializer])
        for i in range(35):
            q.put('var%d' % i)

        for _ in range(15):
            q.get()

        q = Queue(self.path, chunksize=10, **serializer_params[serializer])
        self.assertEqual(q.qsize(), 35)

        for _ in range(15):
            q.get()
        # the first tail file gets removed after task_done
        q.task_done()
        for _ in range(16):
            q.get()
        # the second and third files get removed after task_done
        q.task_done()
        self.assertEqual(q.qsize(), 4)

    def test_protocol(self):
        # test that protocol is set properly
        expect_protocol = 2 if sys.version_info[0] == 2 else 4
        self.assertEqual(
            persistqueue.serializers.pickle.protocol,
            expect_protocol,
        )

        # test that protocol is used properly
        serializer = namedtuple("Serializer", ["dump", "load"])(
                persistqueue.serializers.pickle.dump, lambda fp: fp.read())

        q = Queue(path=self.path, serializer=serializer)
        q.put(b'a')
        self.assertEqual(q.get(), pickle.dumps(b'a', protocol=expect_protocol))
