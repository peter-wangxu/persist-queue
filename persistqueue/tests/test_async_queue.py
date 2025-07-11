"""Asynchronous queue test module."""
import asyncio
import tempfile
import os
import pytest
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
                item_id = await queue.put({"name": "test", "value": 123})
                assert item_id is not None
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
                item_id = await queue.put({"name": "original", "value": 1})

                # Update data
                await queue.update({"name": "updated", "value": 2},
                                   item_id)

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
                item_id = await queue.put("test_data")

                # Get raw data
                raw_item = await queue.get(raw=True)
                assert "pqid" in raw_item
                assert "data" in raw_item
                assert "timestamp" in raw_item
                assert raw_item["data"] == "test_data"
                assert raw_item["pqid"] == item_id
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


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__])
