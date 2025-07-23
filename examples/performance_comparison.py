#!/usr/bin/env python3
"""
Synchronous and asynchronous queue performance comparison example.

This example demonstrates the performance differences between synchronous
and asynchronous queues in concurrent scenarios.
"""
import asyncio
import time
import tempfile
import os
from persistqueue import Queue, AsyncQueue


def sync_producer_consumer_test(num_items=1000, num_producers=4, num_consumers=4):
    """Synchronous queue performance test."""
    print(f"Sync queue test: {num_items} items, {num_producers} producers, {num_consumers} consumers")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "sync_queue")
        queue = Queue(queue_path)
        
        start_time = time.time()
        
        # Producer function
        def producer(producer_id):
            for i in range(num_items // num_producers):
                queue.put(f"Producer{producer_id}-Item{i}")
        
        # Consumer function
        def consumer(consumer_id):
            for i in range(num_items // num_consumers):
                item = queue.get()
                queue.task_done()
        
        # Create threads
        import threading
        producers = [threading.Thread(target=producer, args=(i,)) for i in range(num_producers)]
        consumers = [threading.Thread(target=consumer, args=(i,)) for i in range(num_consumers)]
        
        # Start all threads
        for p in producers:
            p.start()
        for c in consumers:
            c.start()
        
        # Wait for all threads to complete
        for p in producers:
            p.join()
        for c in consumers:
            c.join()
        
        # Wait for queue to empty
        queue.join()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Sync queue completion time: {duration:.2f} seconds")
        print(f"Throughput: {num_items / duration:.0f} items/second")
        
        return duration


async def async_producer_consumer_test(num_items=1000, num_producers=4, num_consumers=4):
    """Asynchronous queue performance test."""
    print(f"Async queue test: {num_items} items, {num_producers} producers, {num_consumers} consumers")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "async_queue")
        
        async with AsyncQueue(queue_path) as queue:
            start_time = time.time()
            
            # Producer coroutine
            async def producer(producer_id):
                for i in range(num_items // num_producers):
                    await queue.put(f"Producer{producer_id}-Item{i}")
            
            # Consumer coroutine
            async def consumer(consumer_id):
                for i in range(num_items // num_consumers):
                    item = await queue.get()
                    await queue.task_done()
            
            # Create all coroutines
            producers = [producer(i) for i in range(num_producers)]
            consumers = [consumer(i) for i in range(num_consumers)]
            
            # Run all coroutines concurrently
            await asyncio.gather(*producers, *consumers)
            
            # Wait for queue to empty
            await queue.join()
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Async queue completion time: {duration:.2f} seconds")
            print(f"Throughput: {num_items / duration:.0f} items/second")
            
            return duration


async def mixed_workload_test():
    """Mixed workload test."""
    print("\n=== Mixed Workload Test ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "mixed_queue")
        
        async with AsyncQueue(queue_path) as queue:
            start_time = time.time()
            
            # Simulate I/O intensive tasks
            async def io_worker(worker_id):
                for i in range(10):
                    await queue.put(f"IO Task{worker_id}-{i}")
                    await asyncio.sleep(0.01)  # Simulate I/O delay
                    item = await queue.get()
                    await queue.task_done()
                    await asyncio.sleep(0.01)  # Simulate I/O delay
            
            # Simulate CPU intensive tasks
            async def cpu_worker(worker_id):
                for i in range(10):
                    # Simulate CPU computation
                    result = sum(range(1000))
                    await queue.put(f"CPU Task{worker_id}-{i}-Result{result}")
                    item = await queue.get()
                    await queue.task_done()
            
            # Run different types of tasks concurrently
            io_workers = [io_worker(i) for i in range(3)]
            cpu_workers = [cpu_worker(i) for i in range(3)]
            
            await asyncio.gather(*io_workers, *cpu_workers)
            await queue.join()
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Mixed workload completion time: {duration:.2f} seconds")


async def memory_usage_test():
    """Memory usage test."""
    print("\n=== Memory Usage Test ===")
    
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "memory_queue")
        
        async with AsyncQueue(queue_path) as queue:
            # Put large amount of data
            for i in range(10000):
                await queue.put(f"Data item{i}" * 100)  # 100 characters per item
            
            # Get memory usage after putting
            memory_after_put = process.memory_info().rss / 1024 / 1024
            
            # Consume all data
            for i in range(10000):
                item = await queue.get()
                await queue.task_done()
            
            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024
            
            print(f"Initial memory: {initial_memory:.1f} MB")
            print(f"Memory after putting: {memory_after_put:.1f} MB")
            print(f"Memory after consuming: {final_memory:.1f} MB")
            print(f"Memory increase: {memory_after_put - initial_memory:.1f} MB")


async def main():
    """Main function."""
    print("Persistent Queue Performance Comparison Test")
    print("=" * 50)
    
    # Test parameters
    test_configs = [
        (100, 2, 2),
        (500, 4, 4),
        (1000, 8, 8),
    ]
    
    results = []
    
    for num_items, num_producers, num_consumers in test_configs:
        print(f"\nTest configuration: {num_items} items, {num_producers} producers, {num_consumers} consumers")
        print("-" * 60)
        
        # Sync test
        sync_time = sync_producer_consumer_test(num_items, num_producers, num_consumers)
        
        # Async test
        async_time = await async_producer_consumer_test(num_items, num_producers, num_consumers)
        
        # Calculate performance improvement
        speedup = sync_time / async_time
        results.append({
            'config': (num_items, num_producers, num_consumers),
            'sync_time': sync_time,
            'async_time': async_time,
            'speedup': speedup
        })
        
        print(f"Performance improvement: {speedup:.2f}x")
    
    # Run other tests
    await mixed_workload_test()
    await memory_usage_test()
    
    # Summary
    print("\n" + "=" * 50)
    print("Performance Test Summary:")
    for result in results:
        config = result['config']
        print(f"Configuration {config}: Sync {result['sync_time']:.2f}s, "
              f"Async {result['async_time']:.2f}s, Improvement {result['speedup']:.2f}x")


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main()) 