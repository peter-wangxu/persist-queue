#!/usr/bin/env python3
"""
Asynchronous API installation and functionality test script.

This script is used to verify that the async API is correctly installed and working.
"""

import sys
import asyncio
import tempfile
import os

def test_imports():
    """Test imports."""
    print("Testing imports...")
    
    try:
        from persistqueue import AsyncQueue, AsyncSQLiteQueue
        print("✓ Async queue classes imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Async queue classes import failed: {e}")
        return False

def test_dependencies():
    """Test dependencies."""
    print("Testing dependencies...")
    
    try:
        import aiofiles
        print("✓ aiofiles imported successfully")
    except ImportError:
        print("✗ aiofiles not installed, please run: pip install aiofiles")
        return False
    
    try:
        import aiosqlite
        print("✓ aiosqlite imported successfully")
    except ImportError:
        print("✗ aiosqlite not installed, please run: pip install aiosqlite")
        return False
    
    return True

async def test_async_queue():
    """Test async file queue."""
    print("Testing async file queue...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_async_queue")
            
            async with AsyncQueue(queue_path) as queue:
                # Test basic operations
                await queue.put("test data")
                assert await queue.qsize() == 1
                
                item = await queue.get()
                assert item == "test data"
                await queue.task_done()
                
                assert await queue.empty()
                print("✓ Async file queue test passed")
                return True
    except Exception as e:
        print(f"✗ Async file queue test failed: {e}")
        return False

async def test_async_sqlite_queue():
    """Test async SQLite queue."""
    print("Testing async SQLite queue...")
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Test basic operations
                item_id = await queue.put({"name": "test", "value": 123})
                assert item_id is not None
                
                item = await queue.get()
                assert item == {"name": "test", "value": 123}
                await queue.task_done()
                
                # Test update operation
                await queue.update({"name": "updated", "value": 456}, item_id)
                
                print("✓ Async SQLite queue test passed")
                return True
        finally:
            os.unlink(db_path)
    except Exception as e:
        print(f"✗ Async SQLite queue test failed: {e}")
        return False

async def test_concurrent_operations():
    """Test concurrent operations."""
    print("Testing concurrent operations...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_concurrent_queue")
            
            async with AsyncQueue(queue_path) as queue:
                # Producer
                async def producer():
                    for i in range(5):
                        await queue.put(f"item{i}")
                        await asyncio.sleep(0.01)
                
                # Consumer
                async def consumer():
                    items = []
                    for i in range(5):
                        item = await queue.get()
                        items.append(item)
                        await queue.task_done()
                        await asyncio.sleep(0.01)
                    return items
                
                # Run concurrently
                producer_task = asyncio.create_task(producer())
                consumer_task = asyncio.create_task(consumer())
                
                await producer_task
                items = await consumer_task
                
                assert len(items) == 5
                assert all(f"item{i}" in items for i in range(5))
                
                print("✓ Concurrent operations test passed")
                return True
    except Exception as e:
        print(f"✗ Concurrent operations test failed: {e}")
        return False

async def main():
    """Main test function."""
    print("Async API Test")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\nPlease ensure async dependencies are installed:")
        print("pip install aiofiles aiosqlite")
        return False
    
    # Test dependencies
    if not test_dependencies():
        return False
    
    # Test functionality
    tests = [
        test_async_queue(),
        test_async_sqlite_queue(),
        test_concurrent_operations(),
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Check results
    passed = 0
    total = len(results)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"✗ Test {i+1} failed: {result}")
        elif result:
            passed += 1
        else:
            print(f"✗ Test {i+1} failed")
    
    print(f"\nTest results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Async API is working correctly.")
        return True
    else:
        print("❌ Some tests failed, please check installation and configuration.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 