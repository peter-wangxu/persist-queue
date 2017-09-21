# coding=utf-8

"""A thread-safe sqlite3 based persistent queue in Python."""

import logging
import pickle
import sqlite3
import time as _time
import threading

from persistqueue import sqlbase
from persistqueue.exceptions import Empty

sqlite3.enable_callback_tracebacks(True)

log = logging.getLogger(__name__)


class SQLiteQueue(sqlbase.SQLiteBase):
    """SQLite3 based FIFO queue."""

    _TABLE_NAME = 'queue'
    _KEY_COLUMN = '_id'  # the name of the key column, used in DB CRUD
    # SQL to create a table
    _SQL_CREATE = ('CREATE TABLE IF NOT EXISTS {table_name} ('
                   '{key_column} INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'data BLOB, timestamp FLOAT)')
    # SQL to insert a record
    _SQL_INSERT = 'INSERT INTO {table_name} (data, timestamp) VALUES (?, ?)'
    # SQL to select a record
    _SQL_SELECT = ('SELECT {key_column}, data FROM {table_name} '
                   'ORDER BY {key_column} ASC LIMIT 1')

    def put(self, item):
        obj = pickle.dumps(item)
        self._insert_into(obj, _time.time())
        self.put_event.set()

    def _init(self):
        super(SQLiteQueue, self)._init()
        # Action lock to assure multiple action to be *atomic*
        self.action_lock = threading.Lock()

    def _pop(self):
        with self.action_lock:
            row = self._select()
            # Perhaps a sqilite bug, sometimes (None, None) is returned
            # by select, below can avoid these invalid records.
            if row and row[0] is not None:
                self._delete(row[0])
                if not self.auto_commit:
                    # Need to commit if not automatic done by _delete
                    sqlbase.commit_ignore_error(self._putter)
                return row[1]  # pickled data
            return None

    def get(self, block=False):
        unpickled = self._pop()
        item = None
        if unpickled:
            item = pickle.loads(unpickled)
        else:
            if block:
                end = _time.time() + 10.0
                while not unpickled:
                    remaining = end - _time.time()
                    if remaining <= 0.0:
                        raise Empty
                    # wait for no more than 10 seconds
                    self.put_event.wait(remaining)
                    unpickled = self._pop()
                item = pickle.loads(unpickled)

        return item

    def task_done(self):
        self._task_done()

    @property
    def size(self):
        return self._count()

    def qsize(self):
        return self.size

    def __len__(self):
        return self.size


FIFOSQLiteQueue = SQLiteQueue


class FILOSQLiteQueue(SQLiteQueue):
    """SQLite3 based FILO queue."""

    _TABLE_NAME = 'filo_queue'
    # SQL to select a record
    _SQL_SELECT = ('SELECT {key_column}, data FROM {table_name} '
                   'ORDER BY {key_column} DESC LIMIT 1')
