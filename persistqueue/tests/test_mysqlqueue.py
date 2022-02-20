# coding=utf-8
import unittest
import random
from threading import Thread
import time
import sys

from persistqueue.mysqlqueue import MySQLQueue
from persistqueue import Empty

# db config aligned with .circleci/config.yml
db_conf = {
    "host": "127.0.0.1",
    "user": "user",
    "passwd": "passw0rd",
    "db_name": "testqueue",
    # "name": "",
    "port": 3306
}
# for appveyor (windows ci), not able to config use the default
# https://www.appveyor.com/docs/services-databases/#mysql
if sys.platform.startswith('win32'):
    db_conf = {
        "host": "127.0.0.1",
        "user": "root",
        "passwd": "Password12!",
        "db_name": "testqueue",
        # "name": "",
        "port": 3306
    }


class MySQLQueueTest(unittest.TestCase):
    """tests that focus on feature specific to mysql"""

    def setUp(self):
        _name = self.id().split(".")[-1:]
        _name.append(str(time.time()))
        self._table_name = ".".join(_name)
        self.queue_class = MySQLQueue
        self.mysql_queue = MySQLQueue(name=self._table_name,
                                      **db_conf)
        self.queue = self.mysql_queue

    def tearDown(self):
        pass
        tmp_conn = self.mysql_queue.get_pooled_conn()
        tmp_conn.cursor().execute(
            "drop table if exists %s" % self.mysql_queue._table_name)
        tmp_conn.commit()

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
        q = MySQLQueue(name=self._table_name,
                       **db_conf)
        self.assertEqual(1, q.qsize())
        self.assertEqual(b'var1', q.get())

    def test_open_close_1000(self):
        """Write 1000 items, close, reopen checking if all items are there"""

        q = self.queue
        for i in range(1000):
            q.put('var%d' % i)
        self.assertEqual(1000, q.qsize())
        del q
        q = MySQLQueue(name=self._table_name,
                       **db_conf)
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
        """Test mysqlqueue can be used by multiple producers."""

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
        """Test mysqlqueue can be used by multiple consumers."""
        queue = self.queue

        def producer():
            for x in range(1000):
                queue.put('var%d' % x)

        counter = []
        # Set all to 0
        for _ in range(1000):
            counter.append(0)

        def consumer(t_index):
            for i in range(200):
                data = queue.get(block=True)
                self.assertTrue('var' in data)
                counter[t_index * 200 + i] = data

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

    def test_task_done_with_restart(self):
        """Test that items are not deleted before task_done."""

        q = self.queue

        for i in range(1, 11):
            q.put(i)

        self.assertEqual(1, q.get())
        self.assertEqual(2, q.get())
        # size is correct before task_done
        self.assertEqual(8, q.qsize())
        q.task_done()
        # make sure the size still correct
        self.assertEqual(8, q.qsize())

        self.assertEqual(3, q.get())
        # without task done
        del q
        q = MySQLQueue(name=self._table_name,
                       **db_conf)
        # After restart, the qsize and head item are the same
        self.assertEqual(7, q.qsize())
        # After restart, the queue still works
        self.assertEqual(4, q.get())
        self.assertEqual(6, q.qsize())
        # auto_commit=False
        del q
        q = MySQLQueue(name=self._table_name, auto_commit=False,
                       **db_conf)
        self.assertEqual(6, q.qsize())
        # After restart, the queue still works
        self.assertEqual(5, q.get())
        self.assertEqual(5, q.qsize())
        del q
        q = MySQLQueue(name=self._table_name, auto_commit=False,
                       **db_conf)
        # After restart, the queue still works
        self.assertEqual(5, q.get())
        self.assertEqual(5, q.qsize())

    def test_protocol_1(self):
        q = self.queue
        self.assertEqual(q._serializer.protocol,
                         2 if sys.version_info[0] == 2 else 4)

    def test_protocol_2(self):
        q = self.queue
        self.assertEqual(q._serializer.protocol,
                         2 if sys.version_info[0] == 2 else 4)

    def test_json_serializer(self):
        q = self.queue
        x = dict(
            a=1,
            b=2,
            c=dict(
                d=list(range(5)),
                e=[1]
            ))
        q.put(x)
        self.assertEqual(q.get(), x)

    def test_put_0(self):
        q = self.queue
        q.put(0)
        d = q.get(block=False)
        self.assertIsNotNone(d)

    def test_get_id(self):
        q = self.queue
        q.put("val1")
        val2_id = q.put("val2")
        q.put("val3")
        item = q.get(id=val2_id)
        # item id should be 2
        self.assertEqual(val2_id, 2)
        # item should get val2
        self.assertEqual(item, 'val2')

    def test_get_raw(self):
        q = self.queue
        q.put("val1")
        item = q.get(raw=True)
        # item should get val2
        self.assertEqual(True, "pqid" in item)
        self.assertEqual(item.get("data"), 'val1')

    def test_queue(self):
        q = self.queue
        q.put("val1")
        q.put("val2")
        q.put("val3")
        # queue should get the three items
        d = q.queue()
        self.assertEqual(len(d), 3)
        self.assertEqual(d[1].get("data"), "val2")

    def test_update(self):
        q = self.queue
        qid = q.put("val1")
        q.update(item="val2", id=qid)
        item = q.get(id=qid)
        self.assertEqual(item, "val2")
