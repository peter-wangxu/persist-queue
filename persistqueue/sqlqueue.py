# coding=utf-8

"""A thread-safe sqlite3 based persistent queue in Python."""

import logging
import sqlite3
import time as _time
import threading

from persistqueue import sqlbase
from persistqueue.exceptions import Empty

sqlite3.enable_callback_tracebacks(True)

log = logging.getLogger(__name__)

# 10 seconds internal for `wait` of event
TICK_FOR_WAIT = 10


class SQLiteQueue(sqlbase.SQLiteBase):
    """SQLite3 based FIFO queue."""

    _TABLE_NAME = 'queue'
    _KEY_COLUMN = '_id'  # the name of the key column, used in DB CRUD
    # SQL to create a table
    _SQL_CREATE = (
        'CREATE TABLE IF NOT EXISTS {table_name} ('
        '{key_column} INTEGER PRIMARY KEY AUTOINCREMENT, '
        'data BLOB, timestamp FLOAT)'
    )
    # SQL to insert a record
    _SQL_INSERT = 'INSERT INTO {table_name} (data, timestamp) VALUES (?, ?)'
    # SQL to select a record
    _SQL_SELECT_ID = (
        'SELECT {key_column}, data, timestamp FROM {table_name} WHERE'
        ' {key_column} = {rowid}'
    )
    _SQL_SELECT = (
        'SELECT {key_column}, data, timestamp FROM {table_name} '
        'ORDER BY {key_column} ASC LIMIT 1'
    )
    _SQL_SELECT_WHERE = (
        'SELECT {key_column}, data, timestamp FROM {table_name} WHERE'
        ' {column} {op} ? ORDER BY {key_column} ASC LIMIT 1 '
    )
    _SQL_UPDATE = 'UPDATE {table_name} SET data = ? WHERE {key_column} = ?'

    def put(self, item, block=True):
        # block kwarg is noop and only here to align with python's queue
        obj = self._serializer.dumps(item)
        _id = self._insert_into(obj, _time.time())
        self.total += 1
        self.put_event.set()
        return _id

    def put_nowait(self, item):
        return self.put(item, block=False)

    def _init(self):
        super(SQLiteQueue, self)._init()
        # Action lock to assure multiple action to be *atomic*
        self.action_lock = threading.Lock()
        if not self.auto_commit:
            # Refresh current cursor after restart
            head = self._select()
            if head:
                self.cursor = head[0] - 1
            else:
                self.cursor = 0
        self.total = self._count()

    def _pop(self, rowid=None, raw=False):
        with self.action_lock:
            if self.auto_commit:
                row = self._select(rowid=rowid)
                # Perhaps a sqlite3 bug, sometimes (None, None) is returned
                # by select, below can avoid these invalid records.
                if row and row[0] is not None:
                    self._delete(row[0])
                    self.total -= 1
                    item = self._serializer.loads(row[1])
                    if raw:
                        return {
                            'pqid': row[0],
                            'data': item,
                            'timestamp': row[2],
                        }
                    else:
                        return item
            else:
                row = self._select(
                    self.cursor, op=">", column=self._KEY_COLUMN, rowid=rowid
                )
                if row and row[0] is not None:
                    self.cursor = row[0]
                    self.total -= 1
                    item = self._serializer.loads(row[1])
                    if raw:
                        return {
                            'pqid': row[0],
                            'data': item,
                            'timestamp': row[2],
                        }
                    else:
                        return item
            return None

    def update(self, item, id=None):
        if isinstance(item, dict) and "pqid" in item:
            _id = item.get("pqid")
            item = item.get("data")
        if id is not None:
            _id = id
        if _id is None:
            raise ValueError("Provide an id or raw item")
        obj = self._serializer.dumps(item)
        self._update(_id, obj)
        return _id

    def get(self, block=True, timeout=None, id=None, raw=False):
        if isinstance(id, dict) and "pqid" in id:
            rowid = id.get("pqid")
        elif isinstance(id, int):
            rowid = id
        else:
            rowid = None
        if not block:
            serialized = self._pop(raw=raw, rowid=rowid)
            if serialized is None:
                raise Empty
        elif timeout is None:
            # block until a put event.
            serialized = self._pop(raw=raw, rowid=rowid)
            while serialized is None:
                self.put_event.clear()
                self.put_event.wait(TICK_FOR_WAIT)
                serialized = self._pop(raw=raw, rowid=rowid)
        elif timeout < 0:
            raise ValueError("'timeout' must be a non-negative number")
        else:
            # block until the timeout reached
            endtime = _time.time() + timeout
            serialized = self._pop(raw=raw, rowid=rowid)
            while serialized is None:
                self.put_event.clear()
                remaining = endtime - _time.time()
                if remaining <= 0.0:
                    raise Empty
                self.put_event.wait(
                    TICK_FOR_WAIT if TICK_FOR_WAIT < remaining else remaining
                )
                serialized = self._pop(raw=raw, rowid=rowid)
        return serialized

    def get_nowait(self, id=None, raw=False):
        return self.get(block=False, id=id, raw=raw)

    def task_done(self):
        """Persist the current state if auto_commit=False."""
        if not self.auto_commit:
            self._delete(self.cursor, op='<=')
            self._task_done()

    def queue(self):
        rows = self._sql_queue()
        datarows = []
        for row in rows:
            item = {
                'id': row[0],
                'data': self._serializer.loads(row[1]),
                'timestamp': row[2],
            }
            datarows.append(item)
        return datarows

    @property
    def size(self):
        return self.total

    def qsize(self):
        return max(0, self.size)

    def empty(self):
        return self.size == 0

    def __len__(self):
        return self.size


FIFOSQLiteQueue = SQLiteQueue


class FILOSQLiteQueue(SQLiteQueue):
    """SQLite3 based FILO queue."""

    _TABLE_NAME = 'filo_queue'
    # SQL to select a record
    _SQL_SELECT = (
        'SELECT {key_column}, data FROM {table_name} '
        'ORDER BY {key_column} DESC LIMIT 1'
    )


class UniqueQ(SQLiteQueue):
    _TABLE_NAME = 'unique_queue'
    _SQL_CREATE = (
        'CREATE TABLE IF NOT EXISTS {table_name} ('
        '{key_column} INTEGER PRIMARY KEY AUTOINCREMENT, '
        'data BLOB, timestamp FLOAT, UNIQUE (data))'
    )

    def put(self, item):
        obj = self._serializer.dumps(item, sort_keys=True)
        _id = None
        try:
            _id = self._insert_into(obj, _time.time())
        except sqlite3.IntegrityError:
            pass
        else:
            self.total += 1
            self.put_event.set()
        return _id
