# Asynchronous Persistent Queue API

## Overview

Since file I/O is inherently asynchronous, we provide asynchronous versions of the persistent queue API that can better utilize asynchronous programming models. The async API maintains compatibility with existing synchronous APIs while providing better performance and concurrency handling.

## Installation Dependencies

The async API requires additional dependency packages:

```bash
pip install aiofiles aiosqlite
```

Or install complete dependencies:

```bash
pip install -r requirements.txt
```

## Available Async Queue Types

### 1. AsyncQueue - Async File Queue

Asynchronous persistent queue based on files, suitable for high-throughput scenarios.

```python
import asyncio
from persistqueue import AsyncQueue

async def example():
    async with AsyncQueue("/path/to/queue") as queue:
        # Put data
        await queue.put("data item")
        
        # Get data
        item = await queue.get()
        
        # Mark task as done
        await queue.task_done()
        
        # Wait for all tasks to complete
        await queue.join()
```

### 2. AsyncSQLiteQueue - Async SQLite Queue

Asynchronous queue based on SQLite, providing better transaction support and query capabilities.

```python
import asyncio
from persistqueue import AsyncSQLiteQueue

async def example():
    async with AsyncSQLiteQueue("/path/to/queue.db") as queue:
        # Put data, returns record ID
        item_id = await queue.put({"key": "value"})
        
        # Get data
        item = await queue.get()
        
        # Update data
        await queue.update({"key": "new_value"}, item_id)
        
        # Mark task as done
        await queue.task_done()
```

### 3. AsyncFIFOSQLiteQueue - Async FIFO SQLite Queue

First-in-first-out SQLite queue (alias for AsyncSQLiteQueue).

### 4. AsyncFILOSQLiteQueue - Async FILO SQLite Queue

Last-in-first-out SQLite queue.

### 5. AsyncUniqueQ - Async Unique Queue

SQLite queue that ensures no duplicate items.

## API Reference

### AsyncQueue

#### Constructor

```python
AsyncQueue(
    path: str,                    # Queue storage path
    maxsize: int = 0,            # Maximum queue size, 0 means unlimited
    chunksize: int = 100,        # Number of entries in each chunk file
    tempdir: Optional[str] = None, # Temporary file directory
    serializer: Any = pickle,    # Serializer
    autosave: bool = False       # Whether to auto-save
)
```

#### Main Methods

- `async put(item, block=True, timeout=None)` - Put item into queue
- `async put_nowait(item)` - Non-blocking put
- `async get(block=True, timeout=None)` - Get item from queue
- `async get_nowait()` - Non-blocking get
- `async task_done()` - Mark task as done
- `async join()` - Wait for all tasks to complete
- `async qsize()` - Get queue size
- `async empty()` - Check if empty
- `async full()` - Check if full
- `async close()` - Close queue

### AsyncSQLiteQueue

#### Constructor

```python
AsyncSQLiteQueue(
    path: str,                   # Database file path
    name: str = 'default',       # Queue name
    serializer: Any = pickle,    # Serializer
    auto_commit: bool = True     # Whether to auto-commit transactions
)
```

#### Main Methods

- `async put(item, block=True)` - Put item into queue, returns record ID
- `async put_nowait(item)` - Non-blocking put
- `async get(block=True, timeout=None, id=None, raw=False)` - Get item from queue
- `async get_nowait(id=None, raw=False)` - Non-blocking get
- `async update(item, id=None)` - Update item
- `async task_done()` - Mark task as done
- `async qsize()` - Get queue size
- `async empty()` - Check if empty
- `async full()` - Check if full
- `async close()` - Close queue

## Usage Examples

### Basic Usage

```python
import asyncio
import tempfile
import os
from persistqueue import AsyncQueue

async def basic_example():
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "async_queue")
        
        async with AsyncQueue(queue_path) as queue:
            # Producer
            async def producer():
                for i in range(5):
                    await queue.put(f"Task {i}")
                    await asyncio.sleep(0.1)
            
            # Consumer
            async def consumer():
                for i in range(5):
                    item = await queue.get()
                    print(f"Process: {item}")
                    await queue.task_done()
                    await asyncio.sleep(0.2)
            
            # Run concurrently
            await asyncio.gather(producer(), consumer())
            await queue.join()

# Run example
asyncio.run(basic_example())
```

### Multiple Producers and Consumers

```python
async def multi_producer_consumer():
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "multi_queue")
        
        async with AsyncQueue(queue_path) as queue:
            # Multiple producers
            async def producer(producer_id):
                for i in range(3):
                    await queue.put(f"Producer{producer_id}-Task{i}")
                    await asyncio.sleep(0.1)
            
            # Multiple consumers
            async def consumer(consumer_id):
                for i in range(3):
                    item = await queue.get()
                    print(f"Consumer{consumer_id}: {item}")
                    await queue.task_done()
                    await asyncio.sleep(0.2)
            
            # Create multiple producers and consumers
            producers = [producer(i) for i in range(2)]
            consumers = [consumer(i) for i in range(2)]
            
            await asyncio.gather(*producers, *consumers)
            await queue.join()
```

### Timeout Handling

```python
async def timeout_example():
    with tempfile.TemporaryDirectory() as temp_dir:
        queue_path = os.path.join(temp_dir, "timeout_queue")
        
        async with AsyncQueue(queue_path) as queue:
            # Try to get from empty queue with timeout
            try:
                item = await queue.get(timeout=1.0)
                print(f"Got: {item}")
            except Exception as e:
                print(f"Timeout: {e}")
            
            # Put data and try again
            await queue.put("Test data")
            item = await queue.get(timeout=1.0)
            print(f"Successfully got: {item}")
            await queue.task_done()
```

### SQLite Queue Example

```python
async def sqlite_example():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        async with AsyncSQLiteQueue(db_path) as queue:
            # Put data
            item_id = await queue.put({"name": "John", "age": 30})
            print(f"Inserted record ID: {item_id}")
            
            # Get data
            item = await queue.get()
            print(f"Got: {item}")
            
            # Update data
            await queue.update({"name": "Jane", "age": 31}, item_id)
            
            await queue.task_done()
    finally:
        os.unlink(db_path)
```

## Performance Advantages

1. **Non-blocking I/O**: Async API uses non-blocking file operations, avoiding thread blocking
2. **Better concurrency**: Can handle multiple queue operations simultaneously
3. **Resource efficiency**: Reduces thread overhead, improves system resource utilization
4. **Scalability**: Easier to handle large numbers of concurrent connections

## Notes

1. **Serializer**: Current implementation still uses synchronous serializers, which may block when serializing large amounts of data
2. **Dependencies**: Requires installation of `aiofiles` and `aiosqlite` packages
3. **Compatibility**: Async queues use the same storage format as sync queues and can read each other
4. **Error handling**: Exceptions in async operations need appropriate error handling

## Migration Guide

Migrating from sync API to async API:

1. Replace `Queue` with `AsyncQueue`
2. Replace `SQLiteQueue` with `AsyncSQLiteQueue`
3. Add `await` before all queue operations
4. Use `async with` context manager
5. Call queue operations in async functions

```python
# Sync version
from persistqueue import Queue
queue = Queue("/path/to/queue")
queue.put("data")
item = queue.get()
queue.task_done()

# Async version
from persistqueue import AsyncQueue
async with AsyncQueue("/path/to/queue") as queue:
    await queue.put("data")
    item = await queue.get()
    await queue.task_done()
``` 