# coding=utf-8

from persistqueue.sqlqueue import MySQLQueue
from persistqueue.tests.common import CommonCases


class MySQLQueueTest(CommonCases):

    def setUp(self):
        self.queue = MySQLQueue("127.0.0.1", "root", "123456", "testqueu", 33306)

    def tearDown(self):
        self.queue._putter.execute("delete from %s" % self.queue._table_name)
        self.queue._putter.commit()

    def test_1(self):
        q = self.queue
        q.put("peter")
        data = q.get()
        self.assertEqual(data, "peter")

        q.put("yuzhi")
        data = q.get()
        self.assertEqual(data, "yuzhi")
