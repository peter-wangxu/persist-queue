import logging
import os
import sqlite3
import threading
import uuid

from persistqueue.lib import retrying

sqlite3.enable_callback_tracebacks(True)

log = logging.getLogger(__name__)


def with_conditional_transaction(func):
    def _execute(obj, *args, **kwargs):
            with obj.tran_lock:
                if obj.auto_commit:
                    with obj._putter as tran:
                        stat, param = func(obj, *args, **kwargs)
                        tran.execute(stat, param)
                else:
                    stat, param = func(obj, *args, **kwargs)
                    obj._putter.execute(stat, param)
                    # commit_ignore_error(obj._putter)

    return _execute


def commit_ignore_error(conn):
    """Ignore the error of no transaction is active.

    The transaction may be already committed by user's task_done call.
    It's safe to ignore all errors of this kind.
    """
    try:
        conn.commit()
    except sqlite3.OperationalError as ex:
        if 'no transaction is active' in str(ex):
            log.debug(
                'Not able to commit the transaction, '
                'may already be committed.')
        else:
            raise


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
                 timeout=10.0, auto_commit=True):
        """Initiate a queue in sqlite3 or memory.

        :param path: path for storing DB file.
        :param name: the suffix for the table name,
                     table name would be ${_TABLE_NAME}_${name}
        :param multithreading: if set to True, two db connections will be,
                               one for **put** and one for **get**.
        :param timeout: timeout in second waiting for the database lock.
        :param auto_commit: Set to True, if commit is required on every
                            INSERT/UPDATE action, otherwise False, whereas
                            a **task_done** is required to persist changes
                            after **put**.


        """
        self.memory_sql = False
        self.path = path
        self.name = name
        self.timeout = timeout
        self.multithreading = multithreading
        self.auto_commit = auto_commit

        self._init()

    def _init(self):
        """Initialize the tables in DB."""

        if self.path == self._MEMORY:
            self.memory_sql = True
            self.memory_id = uuid.uuid1()
            log.debug("Initializing Sqlite3 Queue in memory.")
        elif not os.path.exists(self.path):
            os.makedirs(self.path)
            log.debug(
                'Initializing Sqlite3 Queue with path {}'.format(self.path))

        self._conn = self._new_db_connection(
            self.path, self.multithreading, self.timeout)
        self._getter = self._conn
        self._putter = self._conn

        self._conn.execute(self._sql_create)
        self._conn.commit()
        # Setup another session only for disk-based queue.
        if self.multithreading:
            if not self.memory_sql:
                self._putter = self._new_db_connection(
                    self.path, self.multithreading, self.timeout)
                # self._putter.isolation_level = None
                # self._putter.isolation_level = ""
        if self.auto_commit is False:
            log.warning('auto_commit=False is still experimental,'
                        'only use it with care.')
            self._getter.isolation_level = "DEFERRED"
            self._putter.isolation_level = "DEFERRED"
        # SQLite3 transaction lock
        self.tran_lock = threading.Lock()
        self.put_event = threading.Event()

    def _new_db_connection(self, path, multithreading, timeout):
        if path == self._MEMORY:
            # try:
            #     conn = sqlite3.connect(
            #         database='file:{0}?cache=shared&mode=memory'.format(
            #             self.memory_id),
            #         timeout=1000,
            #         check_same_thread=not multithreading,
            #         uri=True)
            # except TypeError:
                conn = sqlite3.connect(
                    database=':memory:',
                    timeout=timeout,
                    check_same_thread=not multithreading)
        else:
            conn = sqlite3.connect('{}/data.db'.format(path),
                                   timeout=timeout,
                                   check_same_thread=not multithreading)
            conn.execute('PRAGMA journal_mode=WAL;')
        # conn.set_trace_callback(print)
        return conn

    @retrying(error_clz=sqlite3.OperationalError,
              msg='database .* is locked:', max=3)
    @with_conditional_transaction
    def _insert_into(self, *record):
        return self._sql_insert, record

    @with_conditional_transaction
    def _update(self, key, *args):
        args = list(args) + [key]
        return self._sql_update, args

    @with_conditional_transaction
    def _delete(self, key):
        sql = 'DELETE FROM {} WHERE {} = ?'.format(self._table_name,
                                                   self._key_column)
        return sql, (key,)

    @retrying(error_clz=sqlite3.OperationalError,
              msg='database .* is locked:', max=3)
    def _select(self, *args):
        return self._getter.execute(self._sql_select, args).fetchone()

    def _count(self):
        sql = 'SELECT COUNT({}) FROM {}'.format(self._key_column,
                                                self._table_name)
        row = self._getter.execute(sql).fetchone()
        return row[0] if row else 0

    def _task_done(self):
        """Only required if auto-commit is set as False."""
        commit_ignore_error(self._putter)

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
