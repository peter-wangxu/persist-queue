persist-queue - A thread-safe, disk-based queue for Python
==========================================================

.. image:: https://img.shields.io/circleci/project/github/peter-wangxu/persist-queue/master.svg?label=Linux%20%26%20Mac
    :target: https://circleci.com/gh/peter-wangxu/persist-queue

.. image:: https://img.shields.io/appveyor/ci/peter-wangxu/persist-queue/master.svg?label=Windows
    :target: https://ci.appveyor.com/project/peter-wangxu/persist-queue

.. image:: https://img.shields.io/codecov/c/github/peter-wangxu/persist-queue/master.svg
    :target: https://codecov.io/gh/peter-wangxu/persist-queue

.. image:: https://img.shields.io/pypi/v/persist-queue.svg
    :target: https://pypi.python.org/pypi/persist-queue

``persist-queue`` implements a file-based queue and a serial of sqlite3-based queues. The goals is to achieve following requirements:

* Disk-based: each queued item should be stored in disk in case of any crash.
* Thread-safe: can be used by multi-threaded producers and multi-threaded consumers.
* Recoverable: Items can be read after process restart.
* Green-compatible: can be used in ``greenlet`` or ``eventlet`` environment.

While *queuelib* and *python-pqueue* cannot fulfil all of above. After some try, I found it's hard to achieve based on their current
implementation without huge code change. this is the motivation to start this project.

By default, *persist-queue* use *pickle* object serialization module to support object instances.
Most built-in type, like `int`, `dict`, `list` are able to be persisted by `persist-queue` directly, to support customized objects,
please refer to `Pickling and unpickling extension types(Python2) <https://docs.python.org/2/library/pickle.html#pickling-and-unpickling-normal-class-instances>`_
and `Pickling Class Instances(Python3) <https://docs.python.org/3/library/pickle.html#pickling-class-instances>`_

This project is based on the achievements of `python-pqueue <https://github.com/balena/python-pqueue>`_
and `queuelib <https://github.com/scrapy/queuelib>`_

Slack channels
^^^^^^^^^^^^^^

Join `persist-queue <https://join.slack
.com/t/persist-queue/shared_invite
/enQtOTM0MDgzNTQ0MDg3LTNmN2IzYjQ1MDc0MDYzMjI4OGJmNmVkNWE3ZDBjYzg5MDc0OWUzZDJkYTkwODdkZmYwODdjNjUzMTk3MWExNDE>`_ channel


Requirements
------------
* Python 2.7 or Python 3.x (refer to `Deprecation`_ for future plan)
* Full support for Linux.
* Windows support (with `Caution`_ if ``persistqueue.Queue`` is used).

Features
--------

- Multiple platforms support: Linux, macOS, Windows
- Pure python
- Both filed based queues and sqlite3 based queues are supported
- Filed based queue: multiple serialization protocol support: pickle(default), msgpack, json

Deprecation
-----------
- `Python 3.4 release has reached end of life <https://www.python.org/downloads/release/python-3410/>`_ and
  `DBUtils <https://webwareforpython.github.io/DBUtils/changelog.html>`_ ceased support for `Python 3.4`, `persist queue` drops the support for python 3.4 since version 0.8.0.
  other queue implementations such as file based queue and sqlite3 based queue are still workable.
- `Python 2 was sunset on January 1, 2020 <https://www.python.org/doc/sunset-python-2/>`_, `persist-queue` will drop any Python 2 support in future version `1.0.0`, no new feature will be developed under Python 2.

Installation
------------

from pypi
^^^^^^^^^

.. code-block:: console

    pip install persist-queue
    # for msgpack and mysql support, use following command
    pip install persist-queue[extra]


from source code
^^^^^^^^^^^^^^^^

.. code-block:: console

    git clone https://github.com/peter-wangxu/persist-queue
    cd persist-queue
    # for msgpack support, run 'pip install -r extra-requirements.txt' first
    python setup.py install


Benchmark
---------

Here are the time spent(in seconds) for writing/reading **1000** items to the
disk comparing the sqlite3 and file queue.

- Windows
    - OS: Windows 10
    - Disk: SATA3 SSD
    - RAM: 16 GiB

+---------------+---------+-------------------------+----------------------------+
|               | Write   | Write/Read(1 task_done) | Write/Read(many task_done) |
+---------------+---------+-------------------------+----------------------------+
| SQLite3 Queue | 1.8880  | 2.0290                  | 3.5940                     |
+---------------+---------+-------------------------+----------------------------+
| File Queue    | 4.9520  | 5.0560                  | 8.4900                     |
+---------------+---------+-------------------------+----------------------------+

**windows note**
Performance of Windows File Queue has dramatic improvement since `v0.4.1` due to the
atomic renaming support(3-4X faster)

- Linux
    - OS: Ubuntu 16.04 (VM)
    - Disk: SATA3 SSD
    - RAM:  4 GiB

+---------------+--------+-------------------------+----------------------------+
|               | Write  | Write/Read(1 task_done) | Write/Read(many task_done) |
+---------------+--------+-------------------------+----------------------------+
| SQLite3 Queue | 1.8282 | 1.8075                  | 2.8639                     |
+---------------+--------+-------------------------+----------------------------+
| File Queue    | 0.9123 | 1.0411                  | 2.5104                     |
+---------------+--------+-------------------------+----------------------------+

- Mac OS
    - OS: 10.14 (macOS Mojave)
    - Disk: PCIe SSD
    - RAM:  16 GiB

+---------------+--------+-------------------------+----------------------------+
|               | Write  | Write/Read(1 task_done) | Write/Read(many task_done) |
+---------------+--------+-------------------------+----------------------------+
| SQLite3 Queue | 0.1879 | 0.2115                  | 0.3147                     |
+---------------+--------+-------------------------+----------------------------+
| File Queue    | 0.5158 | 0.5357                  | 1.0446                     |
+---------------+--------+-------------------------+----------------------------+

**note**

- The value above is in seconds for reading/writing *1000* items, the less
  the better
- Above result was got from:

.. code-block:: console

    python benchmark/run_benchmark.py 1000


To see the real performance on your host, run the script under ``benchmark/run_benchmark.py``:

.. code-block:: console

    python benchmark/run_benchmark.py <COUNT, default to 100>


Examples
--------


Example usage with a SQLite3 based queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    >>> import persistqueue
    >>> q = persistqueue.SQLiteQueue('mypath', auto_commit=True)
    >>> q.put('str1')
    >>> q.put('str2')
    >>> q.put('str3')
    >>> q.get()
    'str1'
    >>> del q


Close the console, and then recreate the queue:

.. code-block:: python

   >>> import persistqueue
   >>> q = persistqueue.SQLiteQueue('mypath', auto_commit=True)
   >>> q.get()
   'str2'
   >>>

New functions:
*Available since v0.8.0*

- ``shrink_disk_usage`` perform a ``VACUUM`` against the sqlite, and rebuild the database file, this usually takes long time and frees a lot of disk space after ``get()``


Example usage of SQLite3 based ``UniqueQ``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This queue does not allow duplicate items.

.. code-block:: python

   >>> import persistqueue
   >>> q = persistqueue.UniqueQ('mypath')
   >>> q.put('str1')
   >>> q.put('str1')
   >>> q.size
   1
   >>> q.put('str2')
   >>> q.size
   2
   >>>

Example usage of SQLite3 based ``SQLiteAckQueue``/``UniqueAckQ``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The core functions:

- ``put``: add item to the queue. Returns ``id``
- ``get``: get item from queue and mark as unack.  Returns ``item``, Optional paramaters (``block``, ``timeout``, ``id``, ``next_in_order``, ``raw``)
- ``update``: update an item. Returns ``id``, Paramaters (``item``), Optional parameter if item not in raw format (``id``)
- ``ack``: mark item as acked. Returns ``id``, Parameters (``item`` or ``id``)
- ``nack``: there might be something wrong with current consumer, so mark item as ready and new consumer will get it.  Returns ``id``, Parameters (``item`` or ``id``)
- ``ack_failed``: there might be something wrong during process, so just mark item as failed. Returns ``id``, Parameters (``item`` or ``id``)
- ``clear_acked_data``: perform a sql delete agaist sqlite. It removes 1000 items, while keeping 1000 of the most recent, whose status is ``AckStatus.acked`` (note: this does not shrink the file size on disk) Optional paramters (``max_delete``, ``keep_latest``, ``clear_ack_failed``)
- ``shrink_disk_usage`` perform a ``VACUUM`` against the sqlite, and rebuild the database file, this usually takes long time and frees a lot of disk space after ``clear_acked_data``
- ``queue``: returns the database contents as a Python List[Dict]
- ``active_size``: The active size changes when an item is added (put) and completed (ack/ack_failed) unlike ``qsize`` which changes when an item is pulled (get) or returned (nack).

.. code-block:: python

   >>> import persistqueue
   >>> ackq = persistqueue.SQLiteAckQueue('path')
   >>> ackq.put('str1')
   >>> item = ackq.get()
   >>> # Do something with the item
   >>> ackq.ack(item) # If done with the item
   >>> ackq.nack(item) # Else mark item as `nack` so that it can be proceeded again by any worker
   >>> ackq.ack_failed(item) # Or else mark item as `ack_failed` to discard this item

Parameters:

- ``clear_acked_data``
    - ``max_delete`` (defaults to 1000): This is the LIMIT.  How many items to delete.
    - ``keep_latest`` (defaults to 1000): This is the OFFSET.  How many recent items to keep.
    - ``clear_ack_failed`` (defaults to False): Clears the ``AckStatus.ack_failed`` in addition to the ``AckStatus.ack``.

- ``get``
    - ``raw`` (defaults to False): Returns the metadata along with the record, which includes the id (``pqid``) and timestamp.  On the SQLiteAckQueue, the raw results can be ack, nack, ack_failed similar to the normal return.
    -  ``id`` (defaults to None): Accepts an `id` or a raw item containing ``pqid``.  Will select the item based on the row id.
    -  ``next_in_order`` (defaults to False): Requires the ``id`` attribute.  This option tells the SQLiteAckQueue/UniqueAckQ to get the next item based on  ``id``, not the first available.  This allows the user to get, nack, get, nack and progress down the queue, instead of continuing to get the same nack'd item over again.

``raw`` example:

.. code-block:: python

   >>> q.put('val1')
   >>> d = q.get(raw=True)
   >>> print(d)
   >>> {'pqid': 1, 'data': 'val1', 'timestamp': 1616719225.012912}
   >>> q.ack(d)

``next_in_order`` example:

.. code-block:: python

   >>> q.put("val1")
   >>> q.put("val2")
   >>> q.put("val3")
   >>> item = q.get()
   >>> id = q.nack(item)
   >>> item = q.get(id=id, next_in_order=True)
   >>> print(item)
   >>> val2


Note:

1. The SQLiteAckQueue always uses "auto_commit=True".
2. The Queue could be set in non-block style, e.g. "SQLiteAckQueue.get(block=False, timeout=5)".
3. ``UniqueAckQ`` only allows for unique items

Example usage with a file based queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Parameters:

- ``path``: specifies the directory wher enqueued data persisted.
- ``maxsize``: indicates the maximum size stored in the queue, if maxsize<=0 the queue is unlimited.
- ``chunksize``: indicates how many entries should exist in each chunk file on disk. When a all entries in a chunk file was dequeued by get(), the file would be removed from filesystem.
- ``tempdir``: indicates where temporary files should be stored. The tempdir has to be located on the same disk as the enqueued data in order to obtain atomic operations.
- ``serializer``: controls how enqueued data is serialized.
- ``auto_save``: `True` or `False`. By default, the change is only persisted when task_done() is called. If autosave is enabled, info data is persisted immediately when get() is called. Adding data to the queue with put() will always persist immediately regardless of this setting.

.. code-block:: python

    >>> from persistqueue import Queue
    >>> q = Queue("mypath")
    >>> q.put('a')
    >>> q.put('b')
    >>> q.put('c')
    >>> q.get()
    'a'
    >>> q.task_done()


Close the python console, and then we restart the queue from the same path,

.. code-block:: python

    >>> from persistqueue import Queue
    >>> q = Queue('mypath')
    >>> q.get()
    'b'
    >>> q.task_done()

Example usage with an auto-saving file based queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Available since: v0.5.0*

By default, items added to the queue are persisted during the ``put()`` call,
and items removed from a queue are only persisted when ``task_done()`` is
called.

.. code-block:: python

    >>> from persistqueue import Queue
    >>> q = Queue("mypath")
    >>> q.put('a')
    >>> q.put('b')
    >>> q.get()
    'a'
    >>> q.get()
    'b'

After exiting and restarting the queue from the same path, we see the items
remain in the queue, because ``task_done()`` wasn't called before.

.. code-block:: python

    >>> from persistqueue import Queue
    >>> q = Queue('mypath')
    >>> q.get()
    'a'
    >>> q.get()
    'b'

This can be advantageous. For example, if your program crashes before finishing
processing an item, it will remain in the queue after restarting. You can also
spread out the ``task_done()`` calls for performance reasons to avoid lots of
individual writes.

Using ``autosave=True`` on a file based queue will automatically save on every
call to ``get()``. Calling ``task_done()`` is not necessary, but may still be
used to ``join()`` against the queue.

.. code-block:: python

    >>> from persistqueue import Queue
    >>> q = Queue("mypath", autosave=True)
    >>> q.put('a')
    >>> q.put('b')
    >>> q.get()
    'a'

After exiting and restarting the queue from the same path, only the second item
remains:

.. code-block:: python

    >>> from persistqueue import Queue
    >>> q = Queue('mypath', autosave=True)
    >>> q.get()
    'b'


Example usage with a SQLite3 based dict
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    >>> from persisitqueue import PDict
    >>> q = PDict("testpath", "testname")
    >>> q['key1'] = 123
    >>> q['key2'] = 321
    >>> q['key1']
    123
    >>> len(q)
    2
    >>> del q['key1']
    >>> q['key1']
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "persistqueue\pdict.py", line 58, in __getitem__
        raise KeyError('Key: {} not exists.'.format(item))
    KeyError: 'Key: key1 not exists.'

Close the console and restart the PDict


.. code-block:: python

    >>> from persisitqueue import PDict
    >>> q = PDict("testpath", "testname")
    >>> q['key2']
    321


Multi-thread usage for **SQLite3** based queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from persistqueue import FIFOSQLiteQueue

    q = FIFOSQLiteQueue(path="./test", multithreading=True)

    def worker():
        while True:
            item = q.get()
            do_work(item)

    for i in range(num_worker_threads):
         t = Thread(target=worker)
         t.daemon = True
         t.start()

    for item in source():
        q.put(item)


multi-thread usage for **Queue**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from persistqueue import Queue

    q = Queue()

    def worker():
        while True:
            item = q.get()
            do_work(item)
            q.task_done()

    for i in range(num_worker_threads):
         t = Thread(target=worker)
         t.daemon = True
         t.start()

    for item in source():
        q.put(item)

    q.join()       # block until all tasks are done

Example usage with a MySQL based queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Available since: v0.8.0*

.. code-block:: python

    >>> import persistqueue
    >>> db_conf = {
    >>>     "host": "127.0.0.1",
    >>>     "user": "user",
    >>>     "passwd": "passw0rd",
    >>>     "db_name": "testqueue",
    >>>     # "name": "",
    >>>     "port": 3306
    >>> }
    >>> q = persistqueue.MySQLQueue(name="testtable", **db_conf)
    >>> q.put('str1')
    >>> q.put('str2')
    >>> q.put('str3')
    >>> q.get()
    'str1'
    >>> del q


Close the console, and then recreate the queue:

.. code-block:: python

   >>> import persistqueue
   >>> q = persistqueue.MySQLQueue(name="testtable", **db_conf)
   >>> q.get()
   'str2'
   >>>



**note**

Due to the limitation of file queue described in issue `#89 <https://github.com/peter-wangxu/persist-queue/issues/89>`_,
`task_done` in one thread may acknowledge items in other threads which should not be. Considering the `SQLiteAckQueue` if you have such requirement.


Serialization via msgpack/json
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- v0.4.1: Currently only available for file based Queue
- v0.4.2: Also available for SQLite3 based Queues

.. code-block:: python

    >>> from persistqueue
    >>> q = persistqueue.Queue('mypath', serializer=persistqueue.serializers.msgpack)
    >>> # via json
    >>> # q = Queue('mypath', serializer=persistqueue.serializers.json)
    >>> q.get()
    'b'
    >>> q.task_done()

Explicit resource reclaim
^^^^^^^^^^^^^^^^^^^^^^^^^

For some reasons, an application may require explicit reclamation for file
handles or sql connections before end of execution. In these cases, user can
simply call:
.. code-block:: python

    q = Queue() # or q = persistqueue.SQLiteQueue('mypath', auto_commit=True)
    del q


to reclaim related file handles or sql connections.

Tips
----

``task_done`` is required both for file based queue and SQLite3 based queue (when ``auto_commit=False``)
to persist the cursor of next ``get`` to the disk.


Performance impact
------------------

- **WAL**

  Starting on v0.3.2, the ``persistqueue`` is leveraging the sqlite3 builtin feature
  `WAL <https://www.sqlite.org/wal.html>`_ which can improve the performance
  significantly, a general testing indicates that ``persistqueue`` is 2-4 times
  faster than previous version.

- **auto_commit=False**

  Since persistqueue v0.3.0, a new parameter ``auto_commit`` is introduced to tweak
  the performance for sqlite3 based queues as needed. When specify ``auto_commit=False``, user
  needs to perform ``queue.task_done()`` to persist the changes made to the disk since
  last ``task_done`` invocation.

- **pickle protocol selection**

  From v0.3.6, the ``persistqueue`` will select ``Protocol version 2`` for python2 and ``Protocol version 4`` for python3
  respectively. This selection only happens when the directory is not present when initializing the queue.

Tests
-----

*persist-queue* use ``tox`` to trigger tests.

- Unit test

.. code-block:: console

    tox -e <PYTHON_VERSION>

Available ``<PYTHON_VERSION>``: ``py27``, ``py34``, ``py35``, ``py36``, ``py37``


- PEP8 check

.. code-block:: console

   tox -e pep8


`pyenv <https://github.com/pyenv/pyenv>`_ is usually a helpful tool to manage multiple versions of Python.

Caution
-------

Currently, the atomic operation is supported on Windows while still in experimental,
That's saying, the data in ``persistqueue.Queue`` could be in unreadable state when an incidental failure occurs during ``Queue.task_done``.

**DO NOT put any critical data on persistqueue.queue on Windows**.


Contribution
------------

Simply fork this repo and send PR for your code change(also tests to cover your change), remember to give a title and description of your PR. I am willing to
enhance this project with you :).


License
-------

`BSD <LICENSE>`_

Contributors
------------

`Contributors <https://github.com/peter-wangxu/persist-queue/graphs/contributors>`_

FAQ
---

* ``sqlite3.OperationalError: database is locked`` is raised.

persistqueue open 2 connections for the db if ``multithreading=True``, the
SQLite database is locked until that transaction is committed. The ``timeout``
parameter specifies how long the connection should wait for the lock to go away
until raising an exception. Default time is **10**, increase ``timeout``
when creating the queue if above error occurs.

* sqlite3 based queues are not thread-safe.

The sqlite3 queues are heavily tested under multi-threading environment, if you find it's not thread-safe, please
make sure you set the ``multithreading=True`` when initializing the queue before submitting new issue:).

