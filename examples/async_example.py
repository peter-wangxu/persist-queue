#!/usr/bin/env python3
"""
Asynchronous persistent queue usage examples.

This example demonstrates how to use the async API to handle persistent queues.
Since file I/O is inherently asynchronous, async versions can better utilize
asynchronous programming models.
"""

import asyncio
import tempfile
import os
from persistqueue import AsyncQueue, AsyncSQLiteQueue


async def file_queue_example():
    """File queue example."""
    print("=== File Queue Example ===")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "async_file_queue")
        
        # Use async context manager
        async with AsyncQueue(queue_path) as queue:
            # Producer task
            async def producer():
                for i in range(5):
                    await queue.put(f"Task {i}")
                    print(f"Producer: put task {i}")
                    await asyncio.sleep(0.1)
            
            # Consumer task
            async def consumer():
                for i in range(5):
                    item = await queue.get()
                    print(f"Consumer: got {item}")
                    await queue.task_done()
                    await asyncio.sleep(0.2)
            
            # Run producer and consumer concurrently
            await asyncio.gather(producer(), consumer())
            
            # Wait for all tasks to complete
            await queue.join()
            print("All tasks completed")


async def sqlite_queue_example():
    """SQLite queue example."""
    print("\n=== SQLite Queue Example ===")
    
    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Use async context manager
        async with AsyncSQLiteQueue(db_path) as queue:
            # Producer task
            async def producer():
                for i in range(3):
                    item_id = await queue.put({"id": i, "data": f"Data {i}"})
                    print(f"Producer: put item {i}, ID: {item_id}")
                    await asyncio.sleep(0.1)
            
            # Consumer task
            async def consumer():
                for i in range(3):
                    item = await queue.get()
                    print(f"Consumer: got {item}")
                    await queue.task_done()
                    await asyncio.sleep(0.2)
            
            # Run producer and consumer concurrently
            await asyncio.gather(producer(), consumer())
            
            # Wait for all tasks to complete
            await queue.join()
            print("All tasks completed")
    
    finally:
        # Clean up temporary file
        os.unlink(db_path)


async def concurrent_producers_consumers():
    """Multiple producers and consumers example."""
    print("\n=== Multiple Producers Consumers Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "concurrent_queue")
        
        async with AsyncQueue(queue_path) as queue:
            # Multiple producers
            async def producer(producer_id):
                for i in range(3):
                    await queue.put(f"Producer{producer_id}-Task{i}")
                    print(f"Producer{producer_id}: put task {i}")
                    await asyncio.sleep(0.1)
            
            # Multiple consumers
            async def consumer(consumer_id):
                for i in range(3):
                    item = await queue.get()
                    print(f"Consumer{consumer_id}: got {item}")
                    await queue.task_done()
                    await asyncio.sleep(0.2)
            
            # Create multiple producers and consumers
            producers = [producer(i) for i in range(2)]
            consumers = [consumer(i) for i in range(2)]
            
            # Run concurrently
            await asyncio.gather(*producers, *consumers)
            
            # Wait for all tasks to complete
            await queue.join()
            print("All tasks completed")


async def timeout_example():
    """Timeout example."""
    print("\n=== Timeout Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "timeout_queue")
        
        async with AsyncQueue(queue_path) as queue:
            # Try to get from empty queue with timeout
            try:
                item = await queue.get(timeout=1.0)
                print(f"Got: {item}")
            except Exception as e:
                print(f"Timeout get failed: {e}")
            
            # Put an item
            await queue.put("Test item")
            
            # Try to get again
            try:
                item = await queue.get(timeout=1.0)
                print(f"Successfully got: {item}")
                await queue.task_done()
            except Exception as e:
                print(f"Get failed: {e}")


async def queue_size_monitoring():
    """Queue size monitoring example."""
    print("\n=== Queue Size Monitoring Example ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "monitor_queue")
        
        async with AsyncQueue(queue_path) as queue:
            # Monitoring task
            async def monitor():
                for i in range(10):
                    size = await queue.qsize()
                    is_empty = await queue.empty()
                    is_full = await queue.full()
                    print(f"Queue status: size={size}, empty={is_empty}, full={is_full}")
                    await asyncio.sleep(0.5)
            
            # Producer task
            async def producer():
                for i in range(5):
                    await queue.put(f"Item {i}")
                    await asyncio.sleep(0.3)
            
            # Consumer task
            async def consumer():
                await asyncio.sleep(1)  # Delay start of consumption
                for i in range(5):
                    item = await queue.get()
                    print(f"Consumed: {item}")
                    await queue.task_done()
                    await asyncio.sleep(0.4)
            
            # Run concurrently
            await asyncio.gather(monitor(), producer(), consumer())


async def main():
    """Main function."""
    print("Asynchronous Persistent Queue Examples")
    print("=" * 50)
    
    # Run various examples
    await file_queue_example()
    await sqlite_queue_example()
    await concurrent_producers_consumers()
    await timeout_example()
    await queue_size_monitoring()
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    # Run async main function
    asyncio.run(main()) 