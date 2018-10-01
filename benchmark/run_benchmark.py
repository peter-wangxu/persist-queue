"""This file provides tests to benchmark performance sqlite/file queue
on specific hardware. User can easily evaluate the performance by running this
file directly via `python run_benchmark.py`
"""
from persistqueue import SQLiteQueue
from persistqueue import Queue
import tempfile
import time

BENCHMARK_COUNT = 100


def time_it(func):
    def _exec(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        end = time.time()
        print(
            "\t{} => time used: {:.4f} seconds.".format(
                func.__doc__,
                (end - start)))

    return _exec


class FileQueueBench(object):
    """Benchmark File queue performance."""

    def __init__(self, prefix=None):
        self.path = prefix
    @time_it
    def benchmark_file_write(self):
        """Writing <BENCHMARK_COUNT> items."""

        self.path = tempfile.mkdtemp('b_file_10000')
        q = Queue(self.path)
        for i in range(BENCHMARK_COUNT):
            q.put('bench%d' % i)
        assert q.qsize() == BENCHMARK_COUNT

    @time_it
    def benchmark_file_read_write_false(self):
        """Writing and reading <BENCHMARK_COUNT> items(1 task_done)."""

        self.path = tempfile.mkdtemp('b_file_10000')
        q = Queue(self.path)
        for i in range(BENCHMARK_COUNT):
            q.put('bench%d' % i)

        for i in range(BENCHMARK_COUNT):
            q.get()
        q.task_done()
        assert q.qsize() == 0

    @time_it
    def benchmark_file_read_write_true(self):
        """Writing and reading <BENCHMARK_COUNT> items(many task_done)."""

        self.path = tempfile.mkdtemp('b_file_10000')
        q = Queue(self.path)
        for i in range(BENCHMARK_COUNT):
            q.put('bench%d' % i)

        for i in range(BENCHMARK_COUNT):
            q.get()
            q.task_done()
        assert q.qsize() == 0

    @classmethod
    def run(cls):
        print(cls.__doc__)
        ins = cls()
        for name in sorted(cls.__dict__):
            if name.startswith('benchmark'):
                func = getattr(ins, name)
                func()


class Sqlite3QueueBench(object):
    """Benchmark Sqlite3 queue performance."""

    @time_it
    def benchmark_sqlite_write(self):
        """Writing <BENCHMARK_COUNT> items."""

        self.path = tempfile.mkdtemp('b_sql_10000')
        q = SQLiteQueue(self.path, auto_commit=False)
        for i in range(BENCHMARK_COUNT):
            q.put('bench%d' % i)

        assert q.qsize() == BENCHMARK_COUNT

    @time_it
    def benchmark_sqlite_read_write_false(self):
        """Writing and reading <BENCHMARK_COUNT> items(1 task_done)."""
        self.path = tempfile.mkdtemp('b_sql_10000')
        q = SQLiteQueue(self.path, auto_commit=False)
        for i in range(BENCHMARK_COUNT):
            q.put('bench%d' % i)
        for i in range(BENCHMARK_COUNT):
            q.get()
        q.task_done()
        assert q.qsize() == 0

    @time_it
    def benchmark_sqlite_read_write_true(self):
        """Writing and reading <BENCHMARK_COUNT> items(many task_done)."""
        self.path = tempfile.mkdtemp('b_sql_10000')
        q = SQLiteQueue(self.path, auto_commit=True)
        for i in range(BENCHMARK_COUNT):
            q.put('bench%d' % i)

        for i in range(BENCHMARK_COUNT):
            q.get()
            q.task_done()
        assert q.qsize() == 0

    @classmethod
    def run(cls):
        print(cls.__doc__)
        ins = cls()
        for name in sorted(cls.__dict__):

            if name.startswith('benchmark'):
                func = getattr(ins, name)
                func()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        BENCHMARK_COUNT = int(sys.argv[1])
    print("<BENCHMARK_COUNT> = {}".format(BENCHMARK_COUNT))
    file_bench = FileQueueBench()
    file_bench.run()
    sql_bench = Sqlite3QueueBench()
    sql_bench.run()
