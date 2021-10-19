import unittest

import random
import shutil
import sys
import tempfile
import unittest
from threading import Thread

from persistqueue import SQLiteQueue
from persistqueue.exceptions import Empty


class CommonCases(unittest.TestCase):
    # def __init__(self, queue):
    #     self.queue = queue
    #     super(CommonCases, self).__init__()

    def test_raise_empty(self):
        q = self.queue

        q.put('first')
        d = q.get()
        self.assertEqual('first', d)
        self.assertRaises(Empty, q.get, block=False)
        self.assertRaises(Empty, q.get_nowait)

        # assert with timeout
        self.assertRaises(Empty, q.get, block=True, timeout=1.0)
        # assert with negative timeout
        self.assertRaises(ValueError, q.get, block=True, timeout=-1.0)
        del q

    def test_empty(self):
        q = self.queue
        self.assertEqual(q.empty(), True)

        q.put('first')
        self.assertEqual(q.empty(), False)

        q.get()
        self.assertEqual(q.empty(), True)

    def test_open_close_single(self):
        """Write 1 item, close, reopen checking if same item is there"""

        q = self.queue
        q.put(b'var1')
        del q
        self.assertEqual(1, q.qsize())
        self.assertEqual(b'var1', q.get())

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = self.queue
        for i in range(1000):
            q.put('var%d' % i)

        self.assertEqual(1000, q.qsize())
        del q
        q = SQLiteQueue(self.path)
        self.assertEqual(1000, q.qsize())
        for i in range(1000):
            data = q.get()
            self.assertEqual('var%d' % i, data)
        # assert adding another one still works
        q.put('foobar')
        data = q.get()
        self.assertEqual('foobar', data)

    def test_random_read_write(self):
        """Test random read/write"""

        q = self.queue
        n = 0
        for _ in range(1000):
            if random.random() < 0.5:
                if n > 0:
                    q.get()
                    n -= 1
                else:
                    self.assertRaises(Empty, q.get, block=False)
            else:
                q.put('var%d' % random.getrandbits(16))
                n += 1

    def test_multi_threaded_parallel(self):
        """Create consumer and producer threads, check parallelism"""

        # self.skipTest("Not supported multi-thread.")

        m_queue = self.queue

        def producer():
            for i in range(1000):
                m_queue.put('var%d' % i)

        def consumer():
            for i in range(1000):
                x = m_queue.get(block=True)
                self.assertEqual('var%d' % i, x)

        c = Thread(target=consumer)
        c.start()
        p = Thread(target=producer)
        p.start()
        p.join()
        c.join()
        self.assertEqual(0, m_queue.size)
        self.assertEqual(0, len(m_queue))
        self.assertRaises(Empty, m_queue.get, block=False)

    def test_multi_threaded_multi_producer(self):
        """Test sqlqueue can be used by multiple producers."""
        queue = self.queue

        def producer(seq):
            for i in range(10):
                queue.put('var%d' % (i + (seq * 10)))

        def consumer():
            for _ in range(100):
                data = queue.get(block=True)
                self.assertTrue('var' in data)

        c = Thread(target=consumer)
        c.start()
        producers = []
        for seq in range(10):
            t = Thread(target=producer, args=(seq,))
            t.start()
            producers.append(t)

        for t in producers:
            t.join()

        c.join()

    def test_multiple_consumers(self):
        """Test sqlqueue can be used by multiple consumers."""

        queue = self.queue

        def producer():
            for x in range(1000):
                queue.put('var%d' % x)

        counter = []
        # Set all to 0
        for _ in range(1000):
            counter.append(0)

        def consumer(index):
            for i in range(200):
                data = queue.get(block=True)
                self.assertTrue('var' in data)
                counter[index * 200 + i] = data

        p = Thread(target=producer)
        p.start()
        consumers = []
        for index in range(5):
            t = Thread(target=consumer, args=(index,))
            t.start()
            consumers.append(t)

        p.join()
        for t in consumers:
            t.join()

        self.assertEqual(0, queue.qsize())
        for x in range(1000):
            self.assertNotEqual(0, counter[x],
                                "not 0 for counter's index %s" % x)

        self.assertEqual(len(set(counter)), len(counter))
