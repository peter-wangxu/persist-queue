# coding=utf-8


import os
import pickle
import random
import shutil
import tempfile
import unittest
from threading import Thread

from persistqueue import Queue, Empty


class PersistTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='persistqueue')

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_open_close_single(self):
        """Write 1 item, close, reopen checking if same item is there"""

        q = Queue(self.path)
        q.put('var1')
        del q
        q = Queue(self.path)
        self.assertEqual(1, q.qsize())
        self.assertEqual('var1', q.get())
        q.task_done()

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = Queue(self.path)
        for i in range(1000):
            q.put('var%d' % i)
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
        q.put('foobar')
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
        with self.assertRaises(Empty):
            q.get_nowait()

    def test_garbage_on_head(self):
        """Adds garbage to the queue head and let the internal integrity
        checks fix it"""

        q = Queue(self.path)
        q.put('var1')
        del q

        with open(os.path.join(self.path, 'q00001'), 'a') as fd:
            fd.write('garbage')

        q = Queue(self.path)
        q.put('var2')

        self.assertEqual(2, q.qsize())
        self.assertEqual('var1', q.get())
        q.task_done()
