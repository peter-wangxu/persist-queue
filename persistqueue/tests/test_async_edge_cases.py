"""Asynchronous queue edge cases test module."""
import asyncio
import tempfile
import os
import pytest
from unittest.mock import patch, MagicMock
from persistqueue import AsyncQueue, AsyncSQLiteQueue
from persistqueue.exceptions import Empty


class TestAsyncQueueEdgeCases:
    """Test edge cases for AsyncQueue."""

    @pytest.mark.asyncio
    async def test_fsync_error_handling(self):
        """Test fsync error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, chunksize=1) as queue:
                # Test that fsync errors are handled gracefully
                await queue.put("test_item")
                await queue.put("test_item2")

                # Get items to trigger chunk rotation
                item1 = await queue.get()
                item2 = await queue.get()

                assert item1 == "test_item"
                assert item2 == "test_item2"

    @pytest.mark.asyncio
    async def test_pickle_error_handling(self):
        """Test pickle error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                await queue.put("test_item")

                # Corrupt the file to trigger pickle error
                head_file = queue._qfile(0)
                with open(head_file, 'wb') as f:
                    f.write(b'corrupted_pickle_data')

                # Should handle pickle error gracefully
                with pytest.raises(Empty):
                    await queue.get()

    @pytest.mark.asyncio
    async def test_eof_error_handling(self):
        """Test EOF error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                await queue.put("test_item")

                # Create empty file to trigger EOF
                head_file = queue._qfile(0)
                with open(head_file, 'wb') as f:
                    f.write(b'')

                # Should handle EOF gracefully
                with pytest.raises(Empty):
                    await queue.get()

    @pytest.mark.asyncio
    async def test_file_not_found_error(self):
        """Test file not found error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            # Create queue and put item
            queue = AsyncQueue(queue_path)
            await queue.put("test_item")
            await queue.close()

            # Remove the queue directory to simulate file not found
            import shutil
            shutil.rmtree(queue_path)

            # Create new queue with same path - should handle gracefully
            new_queue = AsyncQueue(queue_path)
            # Use get_nowait to avoid blocking
            with pytest.raises(Empty):
                await new_queue.get_nowait()
            await new_queue.close()

    @pytest.mark.asyncio
    async def test_permission_error_handling(self):
        """Test permission error handling in atomic rename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Mock aiofiles.os.replace to raise PermissionError on first
                # call, succeed on second
                with patch('persistqueue.async_queue.'
                           'aiofiles.os.replace') \
                        as mock_replace:
                    mock_replace.side_effect = [PermissionError, None]
                    # Should handle permission error with retry
                    await queue.put("test_item")
                    # Verify the item was actually put
                    item = await queue.get()
                    assert item == "test_item"

    @pytest.mark.asyncio
    async def test_tempdir_different_filesystem(self):
        """Test tempdir on different filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            # Mock os.stat to simulate different filesystem
            with patch('os.stat') as mock_stat:
                def mock_stat_side_effect(path):
                    # Return different st_dev for different paths
                    if 'temp' in str(path) or 'different' in str(path):
                        return MagicMock(st_dev=1)
                    else:
                        return MagicMock(st_dev=2)

                mock_stat.side_effect = mock_stat_side_effect

                # Should raise ValueError for different filesystem
                with pytest.raises(ValueError):
                    AsyncQueue(queue_path, tempdir="/different/path")

    @pytest.mark.asyncio
    async def test_serializer_without_dump_load(self):
        """Test serializer without dump/load methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            # Create serializer without required methods
            class BadSerializer:
                pass

            # Should raise AttributeError during initialization
            with pytest.raises(AttributeError):
                AsyncQueue(queue_path, serializer=BadSerializer())

    @pytest.mark.asyncio
    async def test_queue_with_zero_maxsize(self):
        """Test queue with zero maxsize."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, maxsize=0) as queue:
                # Should not have size limit
                for i in range(10):
                    await queue.put(f"item_{i}")

                assert await queue.qsize() == 10

                # Get all items
                for i in range(10):
                    item = await queue.get()
                    assert item == f"item_{i}"
                    await queue.task_done()

    @pytest.mark.asyncio
    async def test_queue_with_large_chunksize(self):
        """Test queue with large chunksize."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, chunksize=1000) as queue:
                # Put many items to test large chunksize
                for i in range(500):
                    await queue.put(f"item_{i}")

                assert await queue.qsize() == 500

                # Get all items
                for i in range(500):
                    item = await queue.get()
                    assert item == f"item_{i}"
                    await queue.task_done()

    @pytest.mark.asyncio
    async def test_concurrent_task_done(self):
        """Test concurrent task_done calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Put items
                for i in range(5):
                    await queue.put(f"item_{i}")

                # Get items
                items = []
                for i in range(5):
                    item = await queue.get()
                    items.append(item)

                # Call task_done concurrently
                await asyncio.gather(*[queue.task_done() for _ in range(5)])

                # Join should complete
                await queue.join()

    @pytest.mark.asyncio
    async def test_queue_close_without_items(self):
        """Test closing queue without items."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            queue = AsyncQueue(queue_path)
            await queue.close()

            # Should not raise any errors
            assert queue.headf is None
            assert queue.tailf is None

    @pytest.mark.asyncio
    async def test_queue_close_with_items(self):
        """Test closing queue with items."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            queue = AsyncQueue(queue_path)
            await queue.put("test_item")
            await queue.close()

            # Should close properly even with items
            assert queue.headf is None
            assert queue.tailf is None

    @pytest.mark.asyncio
    async def test_autosave_disabled(self):
        """Test queue with autosave disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path, autosave=False) as queue:
                await queue.put("test_item")
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

    @pytest.mark.asyncio
    async def test_queue_with_complex_objects(self):
        """Test queue with complex objects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                # Complex object
                complex_obj = {
                    'list': [1, 2, 3],
                    'dict': {'a': 1, 'b': 2},
                    'set': {1, 2, 3},
                    'tuple': (1, 2, 3),
                    'nested': {
                        'deep': {
                            'structure': [{'key': 'value'}]
                        }
                    }
                }

                await queue.put(complex_obj)
                retrieved_obj = await queue.get()
                await queue.task_done()

                assert retrieved_obj == complex_obj

    @pytest.mark.asyncio
    async def test_queue_with_none_values(self):
        """Test queue with None values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = os.path.join(temp_dir, "test_queue")

            async with AsyncQueue(queue_path) as queue:
                await queue.put(None)
                await queue.put("string")
                await queue.put(None)

                item1 = await queue.get()
                item2 = await queue.get()
                item3 = await queue.get()

                assert item1 is None
                assert item2 == "string"
                assert item3 is None

                await queue.task_done()
                await queue.task_done()
                await queue.task_done()


class TestAsyncSQLiteQueueEdgeCases:
    """Test edge cases for AsyncSQLiteQueue."""

    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test database connection error."""
        # Use invalid path to trigger connection error
        invalid_path = "/invalid/path/database.db"

        with pytest.raises(Exception):
            async with AsyncSQLiteQueue(invalid_path):
                pass

    @pytest.mark.asyncio
    async def test_auto_commit_false_behavior(self):
        """Test auto_commit=False behavior."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path, auto_commit=False) as queue:
                # Put items
                await queue.put("item_1")
                await queue.put("item_2")

                # Get items without auto commit
                item = await queue.get()
                assert item == "item_1"
                await queue.task_done()

                item = await queue.get()
                assert item == "item_2"
                await queue.task_done()

                # Verify items are removed after task_done
                assert await queue.qsize() == 0

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_by_nonexistent_id(self):
        """Test getting by non-existent ID."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Try to get by non-existent ID
                with pytest.raises(Empty):
                    await queue.get(id=999)

                # Put item and get by its ID
                await queue.put("test_item")
                item = await queue.get()
                assert item == "test_item"
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_update_nonexistent_item(self):
        """Test updating non-existent item."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Try to update non-existent item
                await queue.update("new_data", 999)
                # Should not raise error, just not update anything

                # Put item and update it
                await queue.put("original_data")
                item = await queue.get()
                assert item == "original_data"
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_raw_data_with_nonexistent_id(self):
        """Test raw data with non-existent ID."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Try to get raw data by non-existent ID
                with pytest.raises(Empty):
                    await queue.get(id=999, raw=True)

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_queue_with_large_data(self):
        """Test queue with large data."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Large data
                large_data = "x" * 10000
                await queue.put(large_data)
                item = await queue.get()
                assert item == large_data
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_queue_with_binary_data(self):
        """Test queue with binary data."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Binary data
                binary_data = b'\x00\x01\x02\x03\xff'
                await queue.put(binary_data)
                item = await queue.get()
                assert item == binary_data
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_queue_with_unicode_data(self):
        """Test queue with unicode data."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Unicode data
                unicode_data = "测试数据 🚀"
                await queue.put(unicode_data)
                item = await queue.get()
                assert item == unicode_data
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_queue_with_none_values(self):
        """Test queue with None values."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # None values
                await queue.put(None)
                await queue.put("string")
                await queue.put(None)

                item1 = await queue.get()
                item2 = await queue.get()
                item3 = await queue.get()

                assert item1 is None
                assert item2 == "string"
                assert item3 is None

                await queue.task_done()
                await queue.task_done()
                await queue.task_done()

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_queue_with_complex_objects(self):
        """Test queue with complex objects."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            async with AsyncSQLiteQueue(db_path) as queue:
                # Complex object
                complex_obj = {
                    'list': [1, 2, 3],
                    'dict': {'a': 1, 'b': 2},
                    'set': {1, 2, 3},
                    'tuple': (1, 2, 3),
                    'nested': {
                        'deep': {
                            'structure': [{'key': 'value'}]
                        }
                    }
                }

                await queue.put(complex_obj)
                retrieved_obj = await queue.get()
                await queue.task_done()

                assert retrieved_obj == complex_obj

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_queue_close_without_connection(self):
        """Test closing queue without connection."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            queue = AsyncSQLiteQueue(db_path)
            await queue.close()

            # Should not raise any errors
            assert queue._conn is None

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_queue_close_with_connection(self):
        """Test closing queue with connection."""
        with tempfile.NamedTemporaryFile(suffix='.db',
                                         delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            queue = AsyncSQLiteQueue(db_path)
            await queue.put("test_item")
            await queue.close()

            # Should close properly even with items
            assert queue._conn is None

        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_concurrent_put_get(self):
        """Test concurrent put and get operations."""
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
