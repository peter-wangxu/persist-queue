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

Requirements
------------
* Python 2.7 or Python 3.x.
* Full support for Linux.
* Windows support (with `Caution`_ if ``persistqueue.Queue`` is used).

Features
--------

- Multiple platforms support: Linux, macOS, Windows
- Pure python
- Both filed based queues and sqlite3 based queues are supported
- Filed based queue: multiple serialization protocol support: pickle(default), msgpack, json



Installation
------------

from pypi
^^^^^^^^^

.. code-block:: console

    pip install persist-queue
    # for msgpack support, use following command
    pip install persist-queue[EXTRA]


from source code
^^^^^^^^^^^^^^^^

.. code-block:: console

    git clone https://github.com/peter-wangxu/persist-queue
    cd persist-queue
    python setup.py install


Benchmark
---------

Here are the results for writing/reading **1000** items to the disk comparing the sqlite3 and file queue.

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

- The value above is seconds for reading/writing *1000* items, the less the better.
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

Example usage of SQLite3 based ``SQLiteAckQueue``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The core functions:

- ``get``: get from queue and mark item as unack
- ``ack``: mark item as acked
- ``nack``: there might be something wrong with current consumer, so mark item as ready and new consumer will get it
- ``ack_failed``: there might be something wrong during process, so just mark item as failed.

.. code-block:: python

   >>> import persisitqueue
   >>> ackq = persistqueue.SQLiteAckQueue('path')
   >>> ackq.put('str1')
   >>> item = ackq.get()
   >>> # Do something with the item
   >>> ackq.ack(item) # If done with the item
   >>> ackq.nack(item) # Else mark item as `nack` so that it can be proceeded again by any worker
   >>> ackq.ack_failed() # Or else mark item as `ack_failed` to discard this item



Note: this queue does not support ``auto_commit=True``

Example usage with a file based queue
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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


Serialization via msgpack/json
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**Currently only available for file based Queue**

.. code-block:: python

    >>> from persistqueue
    >>> q = persistqueue.Queue('mypath', persistqueue.serializers.msgpack)
    >>> # via json
    >>> # q = Queue('mypath', persistqueue.serializers.json)
    >>> q.get()
    'b'
    >>> q.task_done()

Tips
----

``task_done`` is required both for filed based queue and SQLite3 based queue (when ``auto_commit=False``)
to persist the cursor of next ``get`` to the disk.


Performance impact
------------------

- **WAL**

  Starting on v0.3.2, the ``persistqueue`` is leveraging the sqlite3 builtin feature
  ``WAL <https://www.sqlite.org/wal.html>`` which can improve the performance
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

