# coding=utf-8

"""A single process, persistent multi-producer, multi-consumer
   queue based on SQLite3."""

import pickle
import sqlite3
import time as _time

from persistqueue import sqlbase

sqlite3.enable_callback_tracebacks(True)


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

    def _pop(self):
        row = self._select()
        if row:
            self._delete(row[0])
            return row[1]  # pickled data
        return None

    def get(self, block=False):
        unpickled = self._pop()
        if unpickled:
            return pickle.loads(unpickled)
        else:
            if block:
                while not unpickled:
                    self.put_event.wait()
                    unpickled = self._pop()
                return pickle.loads(unpickled)
            return None

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
