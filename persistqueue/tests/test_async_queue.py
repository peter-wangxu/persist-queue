"""Asynchronous queue test module."""
import asyncio
import tempfile
import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from persistqueue import AsyncQueue, AsyncSQLiteQueue
from persistqueue.exceptions import Empty, Full


class TestAsyncQueue:
    """Async queue test class."""

    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """Test basic operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Test empty queue
                assert await queue.empty()
                assert await queue.qsize() == 0

                # Test putting data
                await queue.put("test_item")
                assert not await queue.empty()
                assert await queue.qsize() == 1

                # Test getting data
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

                # Test queue is empty again
                assert await queue.empty()

    @pytest.mark.asyncio
    async def test_multiple_items(self):
        """Test multiple items."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Put multiple items
                for i in range(5):
                    await queue.put(f"item_{i}")

                assert await queue.qsize() == 5

                # Get in order
                for i in range(5):
                    item = await queue.get()
                    assert item == f"item_{i}"
                    await queue.task_done()

                assert await queue.empty()

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test timeout functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Test getting from empty queue, should timeout
                with pytest.raises(Empty):
                    await queue.get(timeout=0.1)

                # Put data and should be able to get
                await queue.put("test_item")
                item = await queue.get(timeout=1.0)
                assert item == "test_item"
                await queue.task_done()

    @pytest.mark.asyncio
    async def test_maxsize(self):
        """Test maximum size limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, maxsize=2) as queue:
                # Put two items
                await queue.put("item_1")
                await queue.put("item_2")

                # Try to put third item, should block
                with pytest.raises(Full):
                    await queue.put("item_3", timeout=0.1)

                # Get one item and should be able to continue putting
                item = await queue.get()
                assert item == "item_1"
                await queue.task_done()

                # Now should be able to put third item
                await queue.put("item_3", timeout=1.0)

    @pytest.mark.asyncio
    async def test_producer_consumer(self):
        """Test producer consumer pattern."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                items = []

                # Producer
                async def producer():
                    for i in range(3):
                        await queue.put(f"item_{i}")
                        await asyncio.sleep(0.01)

                # Consumer
                async def consumer():
                    for i in range(3):
                        item = await queue.get()
                        items.append(item)
                        await queue.task_done()
                        await asyncio.sleep(0.01)

                # Run concurrently
                await asyncio.gather(producer(), consumer())
                await queue.join()

                # Verify results
                assert len(items) == 3
                assert "item_0" in items
                assert "item_1" in items
                assert "item_2" in items

    @pytest.mark.asyncio
    async def test_negative_timeout(self):
        """Test negative timeout raises ValueError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                with pytest.raises(ValueError):
                    await queue.get(timeout=-1.0)

                with pytest.raises(ValueError):
                    await queue.put("item", timeout=-1.0)

    @pytest.mark.asyncio
    async def test_put_nowait_get_nowait(self):
        """Test non-blocking operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, maxsize=1) as queue:
                # Test put_nowait
                await queue.put_nowait("item_1")

                # Test put_nowait on full queue
                with pytest.raises(Full):
                    await queue.put_nowait("item_2")

                # Test get_nowait
                item = await queue.get_nowait()
                assert item == "item_1"
                await queue.task_done()

                # Test get_nowait on empty queue
                with pytest.raises(Empty):
                    await queue.get_nowait()

    @pytest.mark.asyncio
    async def test_task_done_and_join(self):
        """Test task_done and join functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Put items
                for i in range(3):
                    await queue.put(f"item_{i}")

                # Get items but don't call task_done
                items = []
                for i in range(3):
                    item = await queue.get()
                    items.append(item)

                # Join should not complete
                join_task = asyncio.create_task(queue.join())
                await asyncio.sleep(0.1)
                assert not join_task.done()

                # Call task_done for all items
                for _ in range(3):
                    await queue.task_done()

                # Join should complete
                await join_task

    @pytest.mark.asyncio
    async def test_chunk_rotation(self):
        """Test chunk rotation when chunksize is reached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, chunksize=2) as queue:
                # Put items to trigger chunk rotation
                for i in range(4):
                    await queue.put(f"item_{i}")

                assert await queue.qsize() == 4

                # Get all items
                for i in range(4):
                    item = await queue.get()
                    assert item == f"item_{i}"
                    await queue.task_done()

    @pytest.mark.asyncio
    async def test_custom_serializer(self):
        """Test custom serializer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            # Create a simple serializer that actually works
            class SimpleSerializer:
                def dump(self, obj, fp):
                    import pickle
                    pickle.dump(obj, fp)

                def load(self, fp):
                    import pickle
                    return pickle.load(fp)

            serializer = SimpleSerializer()

            async with AsyncQueue(queue_path, serializer=serializer) as queue:
                await queue.put("test_item")
                assert await queue.qsize() == 1

                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

    @pytest.mark.asyncio
    async def test_async_serializer(self):
        """Test async serializer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            # Mock async serializer
            mock_serializer = MagicMock()
            mock_serializer.dump = AsyncMock()
            mock_serializer.load = AsyncMock(return_value="test_data")

            async with AsyncQueue(
                        queue_path, serializer=mock_serializer) as queue:
                await queue.put("test_item")
                # dump is called twice: once for the item, once for queue info
                assert mock_serializer.dump.call_count == 2

                item = await queue.get()
                assert item == "test_data"
                await queue.task_done()

    @pytest.mark.asyncio
    async def test_file_operations_error_handling(self):
        """Test file operations error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Test with corrupted pickle data
                await queue.put("test_item")

                # Corrupt the file
                head_file = queue._qfile(0)
                with open(head_file, 'wb') as f:
                    f.write(b'corrupted_data')

                # Should handle corruption gracefully
                with pytest.raises(Empty):
                    await queue.get()

    @pytest.mark.asyncio
    async def test_tempdir_validation(self):
        """Test tempdir validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            # Create queue with different tempdir
            with tempfile.TemporaryDirectory() as temp_dir2:
                # This should work if on same filesystem
                try:
                    async with AsyncQueue(
                                queue_path, tempdir=temp_dir2) as queue:
                        await queue.put("test_item")
                        item = await queue.get()
                        assert item == "test_item"
                        await queue.task_done()
                except ValueError:
                    # If on different filesystem, should raise ValueError
                    pass

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            queue = AsyncQueue(queue_path)
            async with queue:
                await queue.put("test_item")
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

            # Queue should be closed
            assert queue.headf is None
            assert queue.tailf is None

    @pytest.mark.asyncio
    async def test_full_queue_behavior(self):
        """Test full queue behavior with blocking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, maxsize=1) as queue:
                # Put one item
                await queue.put("item_1")

                # Try to put second item with timeout
                with pytest.raises(Full):
                    await queue.put("item_2", timeout=0.1)

                # Get item and put again
                item = await queue.get()
                assert item == "item_1"
                await queue.task_done()

                await queue.put("item_2", timeout=1.0)

    @pytest.mark.asyncio
    async def test_empty_queue_behavior(self):
        """Test empty queue behavior with blocking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Try to get from empty queue
                with pytest.raises(Empty):
                    await queue.get(timeout=0.1)

                # Put item and get it
                await queue.put("test_item")
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent access to queue."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Create multiple producers and consumers
                async def producer(id):
                    for i in range(10):
                        await queue.put(f"item_{id}_{i}")
                        await asyncio.sleep(0.001)

                async def consumer(id):
                    items = []
                    for i in range(10):
                        item = await queue.get()
                        items.append(item)
                        await queue.task_done()
                        await asyncio.sleep(0.001)
                    return items

                # Run multiple producers and consumers
                producers = [producer(i) for i in range(3)]
                consumers = [consumer(i) for i in range(3)]

                await asyncio.gather(*producers)
                results = await asyncio.gather(*consumers)
                await queue.join()

                # Verify all items were processed
                all_items = []
                for result in results:
                    all_items.extend(result)
                assert len(all_items) == 30


class TestAsyncSQLiteQueue:
    """Async SQLite queue test class."""

    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """Test basic operations."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Test empty queue
                assert await queue.empty()
                assert await queue.qsize() == 0

                # Test putting data
                await queue.put({"name": "test", "value": 123})
                assert not await queue.empty()
                assert await queue.qsize() == 1

                # Test getting data
                item = await queue.get()
                assert item == {"name": "test", "value": 123}
                await queue.task_done()

                # Test queue is empty again
                assert await queue.empty()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_update_operation(self):
        """Test update operation."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Put data
                await queue.put({"name": "original", "value": 1})

                # Update data
                await queue.update({"name": "updated", "value": 2}, 1)

                # Get updated data
                item = await queue.get()
                assert item == {"name": "updated", "value": 2}
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_raw_data(self):
        """Test raw data retrieval."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Put data
                await queue.put("test_data")

                # Get raw data
                raw_item = await queue.get(raw=True)
                assert "pqid" in raw_item
                assert "data" in raw_item
                assert "timestamp" in raw_item
                assert raw_item["data"] == "test_data"
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test timeout functionality."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Test getting from empty queue, should timeout
                with pytest.raises(Empty):
                    await queue.get(timeout=0.1)

                # Put data and should be able to get
                await queue.put("test_item")
                item = await queue.get(timeout=1.0)
                assert item == "test_item"
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_negative_timeout(self):
        """Test negative timeout raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                with pytest.raises(ValueError):
                    await queue.get(timeout=-1.0)

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        """Test getting item by specific ID."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Put multiple items
                await queue.put("item_1")
                await queue.put("item_2")

                # Get by specific ID
                item = await queue.get(id=2)
                assert item == "item_2"
                await queue.task_done()

                # Get remaining item
                item = await queue.get()
                assert item == "item_1"
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_by_dict_id(self):
        """Test getting item by dict ID."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Put item
                await queue.put("test_item")

                # Get by dict ID
                item = await queue.get(id={"pqid": 1})
                assert item == "test_item"
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_auto_commit_false(self):
        """Test queue with auto_commit=False."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path, auto_commit=False) as queue:
                # Put item
                await queue.put("test_item")
                assert await queue.qsize() == 1

                # Get item
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_full_and_empty_methods(self):
        """Test full and empty methods."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Test empty queue
                assert await queue.empty()
                assert not await queue.full()

                # Put item
                await queue.put("test_item")
                assert not await queue.empty()
                assert not await queue.full()

                # Get item
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

                # Test empty again
                assert await queue.empty()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager functionality."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            queue = AsyncSQLiteQueue(db_path)
            async with queue:
                await queue.put("test_item")
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

            # Connection should be closed
            assert queue._conn is None

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent access to SQLite queue."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Create multiple producers and consumers
                async def producer(id):
                    for i in range(5):
                        await queue.put(f"item_{id}_{i}")
                        await asyncio.sleep(0.001)

                async def consumer(id):
                    items = []
                    for i in range(5):
                        item = await queue.get()
                        items.append(item)
                        await queue.task_done()
                        await asyncio.sleep(0.001)
                    return items

                # Run multiple producers and consumers
                producers = [producer(i) for i in range(2)]
                consumers = [consumer(i) for i in range(2)]

                await asyncio.gather(*producers)
                results = await asyncio.gather(*consumers)

                # Verify all items were processed
                all_items = []
                for result in results:
                    all_items.extend(result)
                assert len(all_items) == 10

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling scenarios."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Test getting from empty queue
                with pytest.raises(Empty):
                    await queue.get_nowait()

                # Test getting by non-existent ID
                with pytest.raises(Empty):
                    await queue.get(id=999)

        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__])
