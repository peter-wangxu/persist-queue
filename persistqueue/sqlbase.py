import os
import sqlite3
import threading

sqlite3.enable_callback_tracebacks(True)


def with_transaction(func):
    def _execute(obj, *args, **kwargs):
        with obj.tran_lock:
            with obj._putter as tran:
                stat, param = func(obj, *args, **kwargs)
                tran.execute(stat, param)

    return _execute


class SQLiteBase(object):
    """SQLite3 base class."""

    _TABLE_NAME = 'base'  # DB table name
    _KEY_COLUMN = ''  # the name of the key column, used in DB CRUD
    _SQL_CREATE = ''  # SQL to create a table
    _SQL_UPDATE = ''  # SQL to update a record
    _SQL_INSERT = ''  # SQL to insert a record
    _SQL_SELECT = ''  # SQL to select a record
    _MEMORY = ':memory:'  # flag indicating store DB in memory

    def __init__(self, path, name='default', multithreading=False,
                 timeout=10.0):
        """Initiate a queue in sqlite3 or memory.

        :param path: path for storing DB file
        :param multithreading: if set to True, two db connections will be,
                               one for **put** and one for **get**
        """
        self.path = path
        self.name = name
        self.timeout = timeout
        self.multithreading = multithreading

        self._init()

    def _init(self):
        """Initialize the tables in DB."""
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        self._conn = self._new_db_connection(
            self.path, self.multithreading, self.timeout)
        self._getter = self._conn
        self._putter = self._conn
        if self.multithreading:
            self._putter = self._new_db_connection(
                self.path, self.multithreading, self.timeout)
        self._conn.execute(self._sql_create)
        self._conn.commit()
        self.tran_lock = threading.Lock()
        self.put_event = threading.Event()

    def _new_db_connection(self, path, multithreading, timeout):
        if path == self._MEMORY:
            return sqlite3.connect(path,
                                   check_same_thread=not multithreading)
        else:
            return sqlite3.connect('{}/data.db'.format(path),
                                   timeout=timeout,
                                   check_same_thread=not multithreading)

    @with_transaction
    def _insert_into(self, *record):
        return self._sql_insert, record

    @with_transaction
    def _update(self, key, *args):
        args = list(args) + [key]
        return self._sql_update, args

    @with_transaction
    def _delete(self, key):
        sql = 'DELETE FROM {} WHERE {} = ?'.format(self._table_name,
                                                   self._key_column)
        return sql, (key,)

    def _select(self, *args):
        return self._getter.execute(self._sql_select, args).fetchone()

    def _count(self):
        sql = 'SELECT COUNT({}) FROM {}'.format(self._key_column,
                                                self._table_name)
        row = self._putter.execute(sql).fetchone()
        return row[0] if row else 0

    @property
    def _table_name(self):
        return '{}_{}'.format(self._TABLE_NAME, self.name)

    @property
    def _key_column(self):
        return self._KEY_COLUMN

    @property
    def _sql_create(self):
        return self._SQL_CREATE.format(table_name=self._table_name,
                                       key_column=self._key_column)

    @property
    def _sql_insert(self):
        return self._SQL_INSERT.format(table_name=self._table_name,
                                       key_column=self._key_column)

    @property
    def _sql_update(self):
        return self._SQL_UPDATE.format(table_name=self._table_name,
                                       key_column=self._key_column)

    @property
    def _sql_select(self):
        return self._SQL_SELECT.format(table_name=self._table_name,
                                       key_column=self._key_column)
