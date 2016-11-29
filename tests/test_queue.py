# coding=utf-8

import mock
import os
import pickle
import random
import shutil
import tempfile
import unittest
from threading import Thread

from persistqueue import Queue, Empty, Full


class PersistTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='persistqueue')

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_open_close_single(self):
        """Write 1 item, close, reopen checking if same item is there"""

        q = Queue(self.path)
        q.put(b'var1')
        del q
        q = Queue(self.path)
        self.assertEqual(1, q.qsize())
        self.assertEqual(b'var1', q.get())
        q.task_done()

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = Queue(self.path)
        for i in range(1000):
            q.put('var%d' % i)
        self.assertEqual(1000, q.qsize())
        del q
        q = Queue(self.path)
        self.assertEqual(1000, q.qsize())
        for i in range(1000):
            data = q.get()
            self.assertEqual('var%d' % i, data)
            q.task_done()
        with self.assertRaises(Empty):
            q.get_nowait()
        # assert adding another one still works
        q.put(b'foobar')
        data = q.get()

    def test_partial_write(self):
        """Test recovery from previous crash w/ partial write"""

        q = Queue(self.path)
        for i in range(100):
            q.put('var%d' % i)
        del q
        with open(os.path.join(self.path, 'q00000'), 'ab') as f:
            pickle.dump('文字化け', f)
        q = Queue(self.path)
        self.assertEqual(100, q.qsize())
        for i in range(100):
            self.assertEqual('var%d' % i, q.get())
            q.task_done()
        with self.assertRaises(Empty):
            q.get_nowait()

    def test_random_read_write(self):
        """Test random read/write"""

        q = Queue(self.path)
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

    def test_multi_threaded(self):
        """Create consumer and producer threads, check parallelism"""

        q = Queue(self.path)

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

    def test_garbage_on_head(self):
        """Adds garbage to the queue head and let the internal integrity
        checks fix it"""

        q = Queue(self.path)
        q.put(b'var1')
        del q

        with open(os.path.join(self.path, 'q00000'), 'ab') as f:
            f.write(b'garbage')
        q = Queue(self.path)
        q.put(b'var2')

        self.assertEqual(2, q.qsize())
        self.assertEqual(b'var1', q.get())
        q.task_done()

    def test_task_done_too_many_times(self):
        """Test too many task_done called."""
        q = Queue(self.path)
        q.put(b'var1')
        q.get()
        q.task_done()

        with self.assertRaises(ValueError):
            q.task_done()

    def test_get_timeout_negative(self):
        q = Queue(self.path)
        q.put(b'var1')
        with self.assertRaises(ValueError):
            q.get(timeout=-1)

    def test_get_timeout(self):
        """Test when get failed within timeout."""
        q = Queue(self.path)
        q.put(b'var1')
        q.get()
        with self.assertRaises(Empty):
            q.get(timeout=1)

    def test_put_nowait(self):
        """Tests the put_nowait interface."""
        q = Queue(self.path)
        q.put_nowait(b'var1')
        self.assertEqual(b'var1', q.get())
        q.task_done()

    def test_put_maxsize_reached(self):
        """Test that maxsize reached."""
        q = Queue(self.path, maxsize=10)
        for x in range(10):
            q.put(x)

        with self.assertRaises(Full):
            q.put(b'full_now', block=False)

    def test_put_timeout_reached(self):
        """Test put with block and timeout."""
        q = Queue(self.path, maxsize=2)
        for x in range(2):
            q.put(x)

        with self.assertRaises(Full):
            q.put(b'full_and_timeout', block=True, timeout=1)

    def test_put_timeout_negative(self):
        """Test and put with timeout < 0"""
        q = Queue(self.path, maxsize=1)
        with self.assertRaises(ValueError):
            q.put(b'var1', timeout=-1)

    def test_put_block_and_wait(self):
        """Test block until queue is not full."""
        q = Queue(self.path, maxsize=10)

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

    def test_windows_error(self):
        """Test the rename restrictions of Windows"""
        q = Queue(self.path)
        q.put(b'a')
        fake_error = OSError('Cannot create a file when'
                             'that file already exists')
        setattr(fake_error, 'winerror', 183)
        os_rename = os.rename
        i = []

        def fake_remove(src, dst):
            if not i:
                i.append(1)
                raise fake_error
            else:
                i.append(2)
                os_rename(src, dst)

        with mock.patch('os.rename', new=fake_remove):
            q.put(b'b')

        self.assertTrue(b'a', q.get())
        self.assertTrue(b'b', q.get())
