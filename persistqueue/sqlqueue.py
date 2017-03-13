# coding=utf-8

"""A single process, persistent multi-producer, multi-consumer
   queue based on SQLite3."""


import pickle
import sqlite3
import time as _time
import threading

sqlite3.enable_callback_tracebacks(True)


def with_transaction(func):

    def _execute(obj, *args, **kwargs):
        with obj.tran_lock:
            with obj._putter as tran:
                stat, param = func(obj, *args, **kwargs)
                tran.execute(stat, param)
    return _execute


class SQLiteQueue(object):
    """SQLite3 based FIFO queue."""

    TABLE_NAME = 'queue'
    _TABLE_CREATE = ('CREATE TABLE IF NOT EXISTS {} ('
                     '_id INTEGER PRIMARY KEY AUTOINCREMENT, '
                     'data BLOB, timestamp FLOAT)'.format(TABLE_NAME))
    _TABLE_INSERT = ('INSERT INTO {}(data, timestamp) values (?,'
                     '?)'.format(TABLE_NAME))
    _TABLE_SELECT = ('SELECT _id, data from {} order by {} ASC '
                     'limit 1'.format(TABLE_NAME, '_id'))
    _TABLE_DELETE = 'DELETE from {} where _id = ?'.format(TABLE_NAME)
    _TABLE_COUNT = 'SELECT COUNT(_id) from {}'.format(TABLE_NAME)
    MERMORY = ':memory:'

    def __init__(self, path=None, multithreading=False, timeout=10.0):
        """Initiate a queue in sqlite3 or memory.

        :param path: path for storing DB file
        :param multithreading: if set to True, two db connections will be,
                               one for **put** and one for **get**
        """
        self.timeout = timeout
        self._conn = self._new_db_connetion(path, multithreading, timeout)
        self._getter = self._conn
        self._putter = self._conn
        if multithreading:
            self._putter = self._new_db_connetion(path, multithreading,
                                                  timeout)

        self._init()

    def _new_db_connetion(self, path, mulithreading, timeout):
        if path == self.MERMORY:
            return sqlite3.connect(path,
                                   check_same_thread=not mulithreading)
        else:
            return sqlite3.connect('{}/data.db'.format(path),
                                   timeout=timeout,
                                   check_same_thread=not mulithreading)

    def _init(self):
        """Initialize the tables in DB.
        Here is the table:

            _id INTEGER
            data BLOB
            timestamp FLOAT
        """
        self._conn.execute(self._TABLE_CREATE)
        self._conn.commit()
        self.tran_lock = threading.Lock()
        self.put_event = threading.Event()

    @with_transaction
    def _insert_into(self, pickled):
        return self._TABLE_INSERT, (pickled, _time.time())

    @with_transaction
    def _delete(self, _id):
        return self._TABLE_DELETE, (_id,)

    def _select(self):
        row = self._getter.execute(self._TABLE_SELECT).fetchone()
        _id = None
        if row:
            _id = row[0]
        if _id:
            self._delete(_id)
            return row[1]
        return row

    def put(self, item):
        obj = pickle.dumps(item)
        self._insert_into(obj)
        self.put_event.set()

    def get(self, block=False):
        unpickled = self._select()
        if unpickled:
            return pickle.loads(unpickled)
        else:
            if block:
                while not unpickled:
                    self.put_event.wait()
                    unpickled = self._select()
                return pickle.loads(unpickled)
            return None

    @property
    def size(self):
        row = self._putter.execute(self._TABLE_COUNT).fetchone()
        if row:
            return row[0]

        return 0

    def qsize(self):
        return self.size

    def __len__(self):
        return self.size


FIFOSQLiteQueue = SQLiteQueue


class FILOSQLiteQueue(SQLiteQueue):
    """SQLite3 based FILO queue."""

    TABLE_NAME = 'filo_queue'
    _TABLE_CREATE = ('CREATE TABLE IF NOT EXISTS {} ('
                     '_id INTEGER PRIMARY KEY AUTOINCREMENT, '
                     'data BLOB, timestamp FLOAT)'.format(TABLE_NAME))
    _TABLE_INSERT = ('INSERT INTO {}(data, timestamp) values (?,'
                     '?)'.format(TABLE_NAME))
    _TABLE_SELECT = ('SELECT _id, data from {} order by {} DESC '
                     'limit 1'.format(TABLE_NAME, '_id'))
    _TABLE_DELETE = 'DELETE from {} where _id = ?'.format(TABLE_NAME)
    _TABLE_COUNT = 'SELECT COUNT(_id) from {}'.format(TABLE_NAME)
