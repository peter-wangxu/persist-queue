# coding=utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import sqlite3
import time as _time
import threading
import warnings

from . import sqlbase
from .exceptions import Empty

sqlite3.enable_callback_tracebacks(True)

log = logging.getLogger(__name__)

# 10 seconds internal for `wait` of event
TICK_FOR_WAIT = 10


class AckStatus(object):
    inited = '0'
    ready = '1'
    unack = '2'
    acked = '5'
    ack_failed = '9'


class SQLiteAckQueue(sqlbase.SQLiteBase):
    """SQLite3 based FIFO queue with ack support."""

    _TABLE_NAME = 'ack_queue'
    _KEY_COLUMN = '_id'  # the name of the key column, used in DB CRUD
    _MAX_ACKED_LENGTH = 1000
    # SQL to create a table
    _SQL_CREATE = ('CREATE TABLE IF NOT EXISTS {table_name} ('
                   '{key_column} INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'data BLOB, timestamp FLOAT, status INTEGER)')
    # SQL to insert a record
    _SQL_INSERT = 'INSERT INTO {table_name} (data, timestamp, status)'\
        ' VALUES (?, ?, %s)' % AckStatus.inited
    # SQL to select a record
    _SQL_SELECT = ('SELECT {key_column}, data, status FROM {table_name} '
                   'WHERE status < %s '
                   'ORDER BY {key_column} ASC LIMIT 1' % AckStatus.unack)
    _SQL_MARK_ACK_UPDATE = 'UPDATE {table_name} SET status = ?'\
        ' WHERE {key_column} = ?'
    _SQL_SELECT_WHERE = 'SELECT {key_column}, data FROM {table_name}'\
        ' WHERE status < %s AND' \
        ' {column} {op} ? ORDER BY {key_column} ASC'\
        ' LIMIT 1 ' % AckStatus.unack

    def __init__(self, path, auto_resume=True, **kwargs):
        super(SQLiteAckQueue, self).__init__(path, **kwargs)
        if not self.auto_commit:
            warnings.warn("disable auto commit is not support in ack queue")
            self.auto_commit = True
        self._unack_cache = {}
        if auto_resume:
            self.resume_unack_tasks()

    @sqlbase.with_conditional_transaction
    def resume_unack_tasks(self):
        unack_count = self.unack_count()
        if unack_count:
            log.warning("resume %d unack tasks", unack_count)
        sql = 'UPDATE {} set status = ?'\
            ' WHERE status = ?'.format(self._table_name)
        return sql, (AckStatus.ready, AckStatus.unack, )

    def put(self, item):
        obj = self._serializer.dumps(item)
        self._insert_into(obj, _time.time())
        self.total += 1
        self.put_event.set()

    def _init(self):
        super(SQLiteAckQueue, self)._init()
        # Action lock to assure multiple action to be *atomic*
        self.action_lock = threading.Lock()
        self.total = self._count()

    def _count(self):
        sql = 'SELECT COUNT({}) FROM {}'\
            ' WHERE status < ?'.format(self._key_column,
                                       self._table_name)
        row = self._getter.execute(sql, (AckStatus.unack,)).fetchone()
        return row[0] if row else 0

    def _ack_count_via_status(self, status):
        sql = 'SELECT COUNT({}) FROM {}'\
            ' WHERE status = ?'.format(self._key_column,
                                       self._table_name)
        row = self._getter.execute(sql, (status, )).fetchone()
        return row[0] if row else 0

    def unack_count(self):
        return self._ack_count_via_status(AckStatus.unack)

    def acked_count(self):
        return self._ack_count_via_status(AckStatus.acked)

    def ready_count(self):
        return self._ack_count_via_status(AckStatus.ready)

    def ack_failed_count(self):
        return self._ack_count_via_status(AckStatus.ack_failed)

    @sqlbase.with_conditional_transaction
    def _mark_ack_status(self, key, status):
        return self._sql_mark_ack_status, (status, key, )

    @sqlbase.with_conditional_transaction
    def clear_acked_data(self):
        sql = """DELETE FROM {table_name}
            WHERE {key_column} IN (
                SELECT _id FROM {table_name} WHERE status = ?
                ORDER BY {key_column} DESC
                LIMIT 1000 OFFSET {max_acked_length}
            )""".format(table_name=self._table_name,
                        key_column=self._key_column,
                        max_acked_length=self._MAX_ACKED_LENGTH)
        return sql, AckStatus.acked

    @property
    def _sql_mark_ack_status(self):
        return self._SQL_MARK_ACK_UPDATE.format(table_name=self._table_name,
                                                key_column=self._key_column)

    def _pop(self):
        with self.action_lock:
            row = self._select()
            # Perhaps a sqlite3 bug, sometimes (None, None) is returned
            # by select, below can avoid these invalid records.
            if row and row[0] is not None:
                self._mark_ack_status(row[0], AckStatus.unack)
                serialized_data = row[1]
                item = self._serializer.loads(serialized_data)
                self._unack_cache[row[0]] = item
                self.total -= 1
                return item
            return None

    def _find_item_id(self, item):
        for key, value in self._unack_cache.items():
            if value is item:
                return key
        log.warning("Can't find item in unack cache.")
        return None

    def ack(self, item):
        with self.action_lock:
            _id = self._find_item_id(item)
            if _id is None:
                return
            self._mark_ack_status(_id, AckStatus.acked)
            self._unack_cache.pop(_id)

    def ack_failed(self, item):
        with self.action_lock:
            _id = self._find_item_id(item)
            if _id is None:
                return
            self._mark_ack_status(_id, AckStatus.ack_failed)
            self._unack_cache.pop(_id)

    def nack(self, item):
        with self.action_lock:
            _id = self._find_item_id(item)
            if _id is None:
                return
            self._mark_ack_status(_id, AckStatus.ready)
            self._unack_cache.pop(_id)
            self.total += 1

    def get(self, block=True, timeout=None):
        if not block:
            serialized = self._pop()
            if serialized is None:
                raise Empty
        elif timeout is None:
            # block until a put event.
            serialized = self._pop()
            while serialized is None:
                self.put_event.clear()
                self.put_event.wait(TICK_FOR_WAIT)
                serialized = self._pop()
        elif timeout < 0:
            raise ValueError("'timeout' must be a non-negative number")
        else:
            # block until the timeout reached
            endtime = _time.time() + timeout
            serialized = self._pop()
            while serialized is None:
                self.put_event.clear()
                remaining = endtime - _time.time()
                if remaining <= 0.0:
                    raise Empty
                self.put_event.wait(
                    TICK_FOR_WAIT if TICK_FOR_WAIT < remaining else remaining)
                serialized = self._pop()
        item = serialized
        return item

    def task_done(self):
        """Persist the current state if auto_commit=False."""
        if not self.auto_commit:
            self._task_done()

    @property
    def size(self):
        return self.total

    def qsize(self):
        return self.size

    def empty(self):
        return self.size == 0

    def __len__(self):
        return self.size


FIFOSQLiteAckQueue = SQLiteAckQueue


class FILOSQLiteAckQueue(SQLiteAckQueue):
    """SQLite3 based FILO queue with ack support."""

    _TABLE_NAME = 'ack_filo_queue'
    # SQL to select a record
    _SQL_SELECT = ('SELECT {key_column}, data FROM {table_name} '
                   'WHERE status < %s '
                   'ORDER BY {key_column} DESC LIMIT 1' % AckStatus.unack)


class UniqueAckQ(SQLiteAckQueue):
    _TABLE_NAME = 'ack_unique_queue'
    _SQL_CREATE = (
        'CREATE TABLE IF NOT EXISTS {table_name} ('
        '{key_column} INTEGER PRIMARY KEY AUTOINCREMENT, '
        'data BLOB, timestamp FLOAT, status INTEGER, UNIQUE (data))'
    )

    def put(self, item):
        obj = self._serializer.dumps(item, sort_keys=True)
        try:
            self._insert_into(obj, _time.time())
        except sqlite3.IntegrityError:
            pass
        else:
            self.total += 1
            self.put_event.set()
