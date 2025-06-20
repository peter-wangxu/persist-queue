# coding=utf-8
import shutil
import tempfile
import unittest
from persistqueue import PriorityQueue, Empty

class PriorityQueueTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(suffix='priorityqueue')
        self.queue = PriorityQueue(self.path)

    def tearDown(self):
        shutil.rmtree(self.path, ignore_errors=True)

    def test_put_get_priority(self):
        self.queue.put('low', priority=10)
        self.queue.put('high', priority=1)
        self.queue.put('mid', priority=5)
        self.assertEqual(self.queue.qsize(), 3)
        self.assertEqual(self.queue.get(), 'high')  # priority=1
        self.assertEqual(self.queue.get(), 'mid')   # priority=5
        self.assertEqual(self.queue.get(), 'low')   # priority=10
        self.assertTrue(self.queue.empty())
        self.assertRaises(Empty, self.queue.get, block=False)

    def test_put_nowait(self):
        self.queue.put_nowait('a', priority=2)
        self.assertEqual(self.queue.get(), 'a')

    def test_empty(self):
        self.assertTrue(self.queue.empty())
        self.queue.put('x', priority=3)
        self.assertFalse(self.queue.empty())
        self.queue.get()
        self.assertTrue(self.queue.empty())

    def test_qsize(self):
        self.assertEqual(self.queue.qsize(), 0)
        self.queue.put('a', priority=1)
        self.queue.put('b', priority=2)
        self.assertEqual(self.queue.qsize(), 2)
        self.queue.get()
        self.assertEqual(self.queue.qsize(), 1)
        self.queue.get()
        self.assertEqual(self.queue.qsize(), 0) 