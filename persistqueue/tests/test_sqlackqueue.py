# coding=utf-8

import random
import shutil
import sys
import tempfile
import unittest
from threading import Thread

from persistqueue.sqlackqueue import (
    SQLiteAckQueue,
    FILOSQLiteAckQueue,
    UniqueAckQ)
from persistqueue import Empty


class SQLite3AckQueueTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='sqlackqueue')
        self.auto_commit = True

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_raise_empty(self):
        q = SQLiteAckQueue(self.path, auto_commit=self.auto_commit)

        q.put('first')
        d = q.get()
        self.assertEqual('first', d)
        self.assertRaises(Empty, q.get, block=False)

        # assert with timeout
        self.assertRaises(Empty, q.get, block=True, timeout=1.0)
        # assert with negative timeout
        self.assertRaises(ValueError, q.get, block=True, timeout=-1.0)

    def test_empty(self):
        q = SQLiteAckQueue(self.path, auto_commit=self.auto_commit)
        self.assertEqual(q.empty(), True)

        q.put('first')
        self.assertEqual(q.empty(), False)

        q.get()
        self.assertEqual(q.empty(), True)

    def test_open_close_single(self):
        """Write 1 item, close, reopen checking if same item is there"""

        q = SQLiteAckQueue(self.path, auto_commit=self.auto_commit)
        q.put(b'var1')
        del q
        q = SQLiteAckQueue(self.path)
        self.assertEqual(1, q.qsize())
        self.assertEqual(b'var1', q.get())

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = SQLiteAckQueue(self.path, auto_commit=self.auto_commit)
        for i in range(1000):
            q.put('var%d' % i)

        self.assertEqual(1000, q.qsize())
        del q
        q = SQLiteAckQueue(self.path)
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

        q = SQLiteAckQueue(self.path, auto_commit=self.auto_commit)
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

        m_queue = SQLiteAckQueue(
            path=self.path, multithreading=True,
            auto_commit=self.auto_commit
        )

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
        queue = SQLiteAckQueue(
            path=self.path, multithreading=True,
            auto_commit=self.auto_commit
        )

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

        queue = SQLiteAckQueue(
            path=self.path, multithreading=True,
            auto_commit=self.auto_commit
        )

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

    def test_protocol_1(self):
        shutil.rmtree(self.path, ignore_errors=True)
        q = SQLiteAckQueue(path=self.path)
        self.assertEqual(q._serializer.protocol,
                         2 if sys.version_info[0] == 2 else 4)

    def test_protocol_2(self):
        q = SQLiteAckQueue(path=self.path)
        self.assertEqual(q._serializer.protocol,
                         2 if sys.version_info[0] == 2 else 4)

    def test_ack_and_clear(self):
        q = SQLiteAckQueue(path=self.path)
        q._MAX_ACKED_LENGTH = 10
        ret_list = []
        for _ in range(100):
            q.put("val%s" % _)
        for _ in range(100):
            ret_list.append(q.get())
        for ret in ret_list:
            q.ack(ret)
        self.assertEqual(q.acked_count(), 100)
        q.clear_acked_data()
        self.assertEqual(q.acked_count(), 10)

    def test_ack_unknown_item(self):
        q = SQLiteAckQueue(path=self.path)
        q.put("val1")
        val1 = q.get()
        q.ack("val2")
        q.nack("val3")
        q.ack_failed("val4")
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(q.unack_count(), 1)
        q.ack(val1)
        self.assertEqual(q.unack_count(), 0)

    def test_resume_unack(self):
        q = SQLiteAckQueue(path=self.path)
        q.put("val1")
        val1 = q.get()
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(q.unack_count(), 1)
        self.assertEqual(q.ready_count(), 0)
        del q

        q = SQLiteAckQueue(path=self.path, auto_resume=False)
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(q.unack_count(), 1)
        self.assertEqual(q.ready_count(), 0)
        q.resume_unack_tasks()
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(q.unack_count(), 0)
        self.assertEqual(q.ready_count(), 1)
        self.assertEqual(val1, q.get())
        del q

        q = SQLiteAckQueue(path=self.path, auto_resume=True)
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(q.unack_count(), 0)
        self.assertEqual(q.ready_count(), 1)
        self.assertEqual(val1, q.get())

    def test_ack_unack_ack_failed(self):
        q = SQLiteAckQueue(path=self.path)
        q.put("val1")
        q.put("val2")
        q.put("val3")
        val1 = q.get()
        val2 = q.get()
        val3 = q.get()
        # qsize should be zero when all item is getted from q
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(q.unack_count(), 3)
        # nack will let the item requeued as ready status
        q.nack(val1)
        self.assertEqual(q.qsize(), 1)
        self.assertEqual(q.ready_count(), 1)
        # ack failed is just mark item as ack failed
        q.ack_failed(val3)
        self.assertEqual(q.ack_failed_count(), 1)
        # ack should not effect qsize
        q.ack(val2)
        self.assertEqual(q.acked_count(), 1)
        self.assertEqual(q.qsize(), 1)
        # all ack* related action will reduce unack count
        self.assertEqual(q.unack_count(), 0)
        # reget the nacked item
        ready_val = q.get()
        self.assertEqual(ready_val, val1)
        q.ack(ready_val)
        self.assertEqual(q.qsize(), 0)
        self.assertEqual(q.acked_count(), 2)
        self.assertEqual(q.ready_count(), 0)

    def test_put_0(self):
        q = SQLiteAckQueue(path=self.path)
        q.put(0)
        d = q.get(block=False)
        self.assertIsNotNone(d)


class SQLite3QueueInMemory(SQLite3AckQueueTest):
    def setUp(self):
        self.path = ":memory:"
        self.auto_commit = True

    def test_open_close_1000(self):
        self.skipTest('Memory based sqlite is not persistent.')

    def test_open_close_single(self):
        self.skipTest('Memory based sqlite is not persistent.')

    def test_multiple_consumers(self):
        self.skipTest('Skipped due to occasional crash during '
                      'multithreading mode.')

    def test_multi_threaded_multi_producer(self):
        self.skipTest('Skipped due to occasional crash during '
                      'multithreading mode.')

    def test_multi_threaded_parallel(self):
        self.skipTest('Skipped due to occasional crash during '
                      'multithreading mode.')

    def test_task_done_with_restart(self):
        self.skipTest('Skipped due to not persistent.')

    def test_protocol_2(self):
        self.skipTest('In memory queue is always new.')

    def test_resume_unack(self):
        self.skipTest('Memory based sqlite is not persistent.')


class FILOSQLite3AckQueueTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='filo_sqlackqueue')
        self.auto_commit = True

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = FILOSQLiteAckQueue(self.path, auto_commit=self.auto_commit)
        for i in range(1000):
            q.put('var%d' % i)
        self.assertEqual(1000, q.qsize())
        del q
        q = FILOSQLiteAckQueue(self.path)
        self.assertEqual(1000, q.qsize())
        for i in range(1000):
            data = q.get()
            self.assertEqual('var%d' % (999 - i), data)
        # assert adding another one still works
        q.put('foobar')
        data = q.get()
        self.assertEqual('foobar', data)


class SQLite3UniqueAckQueueTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='sqlackqueue')
        self.auto_commit = True

    def test_add_duplicate_item(self):
        q = UniqueAckQ(self.path)
        q.put(1111)
        self.assertEqual(1, q.size)
        # put duplicate item
        q.put(1111)
        self.assertEqual(1, q.size)

        q.put(2222)
        self.assertEqual(2, q.size)

        del q
        q = UniqueAckQ(self.path)
        self.assertEqual(2, q.size)
