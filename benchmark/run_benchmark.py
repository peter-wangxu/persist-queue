"""This file provides tests to benchmark performance sqlite/file queue
on specific hardware. User can easily evaluate the performance by running this
file directly via `python run_benchmark.py`
"""
from persistqueue import SQLiteQueue
from persistqueue import Queue
import tempfile
import time
import sys
import platform
import os
import asyncio

BENCHMARK_COUNT = 100


def time_it(func):
    def _exec(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        end = time.time()
        return end - start
    return _exec


class BenchmarkResult:
    """Store benchmark results for formatted output."""
    
    def __init__(self, platform_info, count):
        self.platform_info = platform_info
        self.count = count
        self.results = {}
    
    def add_result(self, queue_type, test_name, time_taken):
        if queue_type not in self.results:
            self.results[queue_type] = {}
        self.results[queue_type][test_name] = time_taken
    
    def print_rst_table(self):
        """Print results in RST table format."""
        print(f"**{self.platform_info}**")
        print()
        
        # Define column headers
        headers = ["Queue Type", "Write", "Write/Read(1 task_done)", "Write/Read(many task_done)"]
        
        # Create table
        table_width = len(headers)
        separator = "+" + "+".join(["-" * 20] * table_width) + "+"
        
        print(separator)
        print("|" + "|".join(f" {h:<18} " for h in headers) + "|")
        print(separator)
        
        # Add SQLite results
        sqlite_results = self.results.get('SQLite3 Queue', {})
        sqlite_row = [
            "SQLite3 Queue",
            f"{sqlite_results.get('write', 0):.4f}",
            f"{sqlite_results.get('read_write_1', 0):.4f}",
            f"{sqlite_results.get('read_write_many', 0):.4f}"
        ]
        print("|" + "|".join(f" {r:<18} " for r in sqlite_row) + "|")
        
        # Add File Queue results
        file_results = self.results.get('File Queue', {})
        file_row = [
            "File Queue",
            f"{file_results.get('write', 0):.4f}",
            f"{file_results.get('read_write_1', 0):.4f}",
            f"{file_results.get('read_write_many', 0):.4f}"
        ]
        print("|" + "|".join(f" {r:<18} " for r in file_row) + "|")
        
        # Add Async SQLite results
        async_sqlite_results = self.results.get('AsyncSQLiteQueue', {})
        if async_sqlite_results:
            async_sqlite_row = [
                "AsyncSQLiteQueue",
                f"{async_sqlite_results.get('write', 0):.4f}",
                f"{async_sqlite_results.get('read_write_1', 0):.4f}",
                f"{async_sqlite_results.get('read_write_many', 0):.4f}"
            ]
            print("|" + "|".join(f" {r:<18} " for r in async_sqlite_row) + "|")
        
        # Add Async File Queue results
        async_file_results = self.results.get('AsyncFileQueue', {})
        if async_file_results:
            async_file_row = [
                "AsyncFileQueue",
                f"{async_file_results.get('write', 0):.4f}",
                f"{async_file_results.get('read_write_1', 0):.4f}",
                f"{async_file_results.get('read_write_many', 0):.4f}"
            ]
            print("|" + "|".join(f" {r:<18} " for r in async_file_row) + "|")
        
        print(separator)
        print()
    
    def print_console(self):
        """Print results in console format."""
        print(f"Benchmark Results for {self.count} items")
        print(f"Platform: {self.platform_info}")
        print("=" * 60)
        
        for queue_type, tests in self.results.items():
            print(f"\n{queue_type}:")
            for test_name, time_taken in tests.items():
                print(f"  {test_name}: {time_taken:.4f} seconds")
    
    def print_json(self):
        """Print results in JSON format."""
        import json
        output = {
            "platform": self.platform_info,
            "count": self.count,
            "results": self.results
        }
        print(json.dumps(output, indent=2))


class FileQueueBench(object):
    """Benchmark File queue performance."""

    def __init__(self, prefix=None):
        self.path = prefix
        self.results = {}

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
    def benchmark_file_read_write_autosave(self):
        """Writing and reading <BENCHMARK_COUNT> items(autosave)."""
        self.path = tempfile.mkdtemp('b_file_10000')
        q = Queue(self.path, autosave=True)
        for i in range(BENCHMARK_COUNT):
            q.put('bench%d' % i)

        for i in range(BENCHMARK_COUNT):
            q.get()
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

    def run(self, result_collector):
        """Run all file queue benchmarks and collect results."""
        print("Running File Queue benchmarks...")
        
        # Write test
        time_taken = self.benchmark_file_write()
        result_collector.add_result('File Queue', 'write', time_taken)
        
        # Read/Write with 1 task_done
        time_taken = self.benchmark_file_read_write_false()
        result_collector.add_result('File Queue', 'read_write_1', time_taken)
        
        # Read/Write with many task_done
        time_taken = self.benchmark_file_read_write_true()
        result_collector.add_result('File Queue', 'read_write_many', time_taken)


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

    def run(self, result_collector):
        """Run all SQLite queue benchmarks and collect results."""
        print("Running SQLite Queue benchmarks...")
        
        # Write test
        time_taken = self.benchmark_sqlite_write()
        result_collector.add_result('SQLite3 Queue', 'write', time_taken)
        
        # Read/Write with 1 task_done
        time_taken = self.benchmark_sqlite_read_write_false()
        result_collector.add_result('SQLite3 Queue', 'read_write_1', time_taken)
        
        # Read/Write with many task_done
        time_taken = self.benchmark_sqlite_read_write_true()
        result_collector.add_result('SQLite3 Queue', 'read_write_many', time_taken)


class AsyncFileQueueBench(object):
    """Benchmark Async File queue performance."""
    def __init__(self, prefix=None):
        self.path = prefix

    async def benchmark_async_file_write(self):
        """Writing <BENCHMARK_COUNT> items (async)."""
        import tempfile
        from persistqueue.async_queue import AsyncQueue
        self.path = tempfile.mkdtemp('b_async_file_10000')
        async with AsyncQueue(self.path) as q:
            for i in range(BENCHMARK_COUNT):
                await q.put(f'bench{i}')
            assert await q.qsize() == BENCHMARK_COUNT

    async def benchmark_async_file_read_write_1(self):
        """Writing and reading <BENCHMARK_COUNT> items(1 task_done, async)."""
        import tempfile
        from persistqueue.async_queue import AsyncQueue
        self.path = tempfile.mkdtemp('b_async_file_10000')
        async with AsyncQueue(self.path) as q:
            for i in range(BENCHMARK_COUNT):
                await q.put(f'bench{i}')
            for i in range(BENCHMARK_COUNT):
                await q.get()
            await q.task_done()
            assert await q.qsize() == 0

    async def benchmark_async_file_read_write_many(self):
        """Writing and reading <BENCHMARK_COUNT> items(many task_done, async)."""
        import tempfile
        from persistqueue.async_queue import AsyncQueue
        self.path = tempfile.mkdtemp('b_async_file_10000')
        async with AsyncQueue(self.path) as q:
            for i in range(BENCHMARK_COUNT):
                await q.put(f'bench{i}')
            for i in range(BENCHMARK_COUNT):
                await q.get()
                await q.task_done()
            assert await q.qsize() == 0

    async def run(self, result_collector):
        print("Running Async File Queue benchmarks...")
        import time
        # Write test
        start = time.time()
        await self.benchmark_async_file_write()
        result_collector.add_result('AsyncFileQueue', 'write', time.time() - start)
        # Read/Write with 1 task_done
        start = time.time()
        await self.benchmark_async_file_read_write_1()
        result_collector.add_result('AsyncFileQueue', 'read_write_1', time.time() - start)
        # Read/Write with many task_done
        start = time.time()
        await self.benchmark_async_file_read_write_many()
        result_collector.add_result('AsyncFileQueue', 'read_write_many', time.time() - start)

class AsyncSqliteQueueBench(object):
    """Benchmark Async SQLite queue performance."""
    async def benchmark_async_sqlite_write(self):
        """Writing <BENCHMARK_COUNT> items (async)."""
        import tempfile
        from persistqueue.async_sqlqueue import AsyncSQLiteQueue
        self.path = tempfile.mktemp(suffix='.db', prefix='b_async_sql_10000')
        async with AsyncSQLiteQueue(self.path) as q:
            for i in range(BENCHMARK_COUNT):
                await q.put(f'bench{i}')
            assert await q.qsize() == BENCHMARK_COUNT

    async def benchmark_async_sqlite_read_write_1(self):
        """Writing and reading <BENCHMARK_COUNT> items(1 task_done, async)."""
        import tempfile
        from persistqueue.async_sqlqueue import AsyncSQLiteQueue
        self.path = tempfile.mktemp(suffix='.db', prefix='b_async_sql_10000')
        async with AsyncSQLiteQueue(self.path) as q:
            for i in range(BENCHMARK_COUNT):
                await q.put(f'bench{i}')
            for i in range(BENCHMARK_COUNT):
                await q.get()
            await q.task_done()
            assert await q.qsize() == 0

    async def benchmark_async_sqlite_read_write_many(self):
        """Writing and reading <BENCHMARK_COUNT> items(many task_done, async)."""
        import tempfile
        from persistqueue.async_sqlqueue import AsyncSQLiteQueue
        self.path = tempfile.mktemp(suffix='.db', prefix='b_async_sql_10000')
        async with AsyncSQLiteQueue(self.path) as q:
            for i in range(BENCHMARK_COUNT):
                await q.put(f'bench{i}')
            for i in range(BENCHMARK_COUNT):
                await q.get()
                await q.task_done()
            assert await q.qsize() == 0

    async def run(self, result_collector):
        print("Running Async SQLite Queue benchmarks...")
        import time
        # Write test
        start = time.time()
        await self.benchmark_async_sqlite_write()
        result_collector.add_result('AsyncSQLiteQueue', 'write', time.time() - start)
        # Read/Write with 1 task_done
        start = time.time()
        await self.benchmark_async_sqlite_read_write_1()
        result_collector.add_result('AsyncSQLiteQueue', 'read_write_1', time.time() - start)
        # Read/Write with many task_done
        start = time.time()
        await self.benchmark_async_sqlite_read_write_many()
        result_collector.add_result('AsyncSQLiteQueue', 'read_write_many', time.time() - start)


def get_platform_info():
    """Get platform information for benchmark results."""
    system = platform.system()
    release = platform.release()
    
    if system == "Windows":
        return f"Windows {release}"
    elif system == "Darwin":
        return f"macOS {release}"
    elif system == "Linux":
        # Try to get distribution info
        try:
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('PRETTY_NAME'):
                        distro = line.split('=')[1].strip().strip('"')
                        return f"{distro}"
        except:
            pass
        return f"Linux {release}"
    else:
        return f"{system} {release}"


def main():
    """Main benchmark function."""
    global BENCHMARK_COUNT
    
    # Parse command line arguments
    output_format = 'console'
    if len(sys.argv) > 1:
        BENCHMARK_COUNT = int(sys.argv[1])
    if len(sys.argv) > 2:
        output_format = sys.argv[2]
    
    print(f"Benchmarking {BENCHMARK_COUNT} items...")
    
    # Get platform info
    platform_info = get_platform_info()
    
    # Create result collector
    results = BenchmarkResult(platform_info, BENCHMARK_COUNT)
    
    # Run benchmarks
    file_bench = FileQueueBench()
    file_bench.run(results)
    
    sql_bench = Sqlite3QueueBench()
    sql_bench.run(results)
    
    # Async benchmarks
    async def run_async_bench():
        async_file_bench = AsyncFileQueueBench()
        await async_file_bench.run(results)
        async_sql_bench = AsyncSqliteQueueBench()
        await async_sql_bench.run(results)
    asyncio.run(run_async_bench())
    
    # Output results
    if output_format == 'rst':
        results.print_rst_table()
    elif output_format == 'json':
        results.print_json()
    else:
        results.print_console()


if __name__ == '__main__':
    main()
