from .sqlbase import SQLBase
from dbutils.pooled_db import PooledDB
import threading
import time as _time

from persistqueue.exceptions import Empty

import persistqueue

# 10 seconds internal for `wait` of event
TICK_FOR_WAIT = 10


class MySQLQueue(SQLBase):
    """Mysql(or future standard dbms) based FIFO queue."""
    _TABLE_NAME = 'queue'
    _KEY_COLUMN = '_id'  # the name of the key column, used in DB CRUD
    # SQL to create a table
    _SQL_CREATE = (
        'CREATE TABLE IF NOT EXISTS {table_name} ('
        '{key_column} INTEGER PRIMARY KEY AUTO_INCREMENT, '
        'data BLOB, timestamp FLOAT)')
    # SQL to insert a record
    _SQL_INSERT = 'INSERT INTO {table_name} (data, timestamp) VALUES (%s, %s)'
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
    _SQL_UPDATE = 'UPDATE {table_name} SET data = %s WHERE {key_column} = %s'

    _SQL_DELETE = 'DELETE FROM {table_name} WHERE {key_column} {op} %s'

    def __init__(self, host, user, passwd, db_name, name=None,
                 port=3306,
                 charset='utf8mb4',
                 serializer=persistqueue.serializers.pickle,
                 ):
        self.name = name if name else "sql"
        self.host = host
        self.user = user
        self.passwd = passwd
        self.db_name = db_name
        self.name = name
        self.port = port
        self.charset = charset
        self._serializer = serializer
        self.auto_commit = True

        # SQLite3 transaction lock
        self.tran_lock = threading.Lock()
        self.put_event = threading.Event()
        # Action lock to assure multiple action to be *atomic*
        self.action_lock = threading.Lock()

        self._connection_pool = None
        self._getter = None
        self._putter = None
        self._new_db_connection()

    def _new_db_connection(self):
        try:
            import pymysql
        except ImportError:
            print(
                "Please install mysql library via "
                "'pip install PyMySQL'")
            raise
        db_pool = PooledDB(pymysql, 2, 10, 5, 10, True,
                           host=self.host, port=self.port, user=self.user,
                           passwd=self.passwd, database=self.db_name,
                           charset=self.charset
                           )
        self._connection_pool = db_pool
        conn = db_pool.connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        _ = cursor.fetchone()
        # create table automatically
        cursor.execute(self._sql_create)
        conn.commit()
        # switch to the desired db
        cursor.execute("use %s" % self.db_name)
        self._putter = MySQLConn(queue=self)
        self._getter = self._putter

    def put(self, item, block=True):
        # block kwarg is noop and only here to align with python's queue
        obj = self._serializer.dumps(item)
        _id = self._insert_into(obj, _time.time())
        self.put_event.set()
        return _id

    def put_nowait(self, item):
        return self.put(item, block=False)

    def _init(self):
        # super(SQLBase, self)._init()
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

    def get_pooled_conn(self):
        return self._connection_pool.connection()

    def _pop(self, rowid=None, raw=False):
        with self.action_lock:
            row = self._select(rowid=rowid)
            # Perhaps a sqlite3 bug, sometimes (None, None) is returned
            # by select, below can avoid these invalid records.
            if row and row[0] is not None:
                self._delete(row[0])
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
        _id = None
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
        return self._count()

    def qsize(self):
        return max(0, self.size)

    def empty(self):
        return self.size == 0

    def __len__(self):
        return self.size


class MySQLConn(object):
    """MySqlConn defines a common structure for
    both mysql and sqlite3 connections.

    used to mitigate the interface differences between drivers/db
    """

    def __init__(self, queue=None, conn=None):
        if queue is not None:
            self._conn = queue.get_pooled_conn()
        else:
            self._conn = conn
        self._queue = queue
        self._cursor = None
        self.closed = False

    def __enter__(self):
        self._cursor = self._conn.cursor()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # do not commit() but to close() , keep same behavior
        # with dbutils
        self._cursor.close()

    def execute(self, *args, **kwargs):
        conn = None
        if self._queue is not None:
            conn = self._queue.get_pooled_conn()
        else:
            conn = self._conn
        cursor = conn.cursor()
        cursor.execute(*args, **kwargs)
        return cursor

    def close(self):
        # 提交事务
        if not self.closed:
            self._conn.close()
        self.closed = True

    def commit(self):
        if not self.closed:
            self._conn.commit()
