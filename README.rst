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

*persist-queue* use *pickle* object serialization module to support object instances.
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

Installation
------------

from pypi
^^^^^^^^^

.. code-block:: console

    pip install persist-queue

from source code
^^^^^^^^^^^^^^^^

.. code-block:: console

    git clone https://github.com/peter-wangxu/persist-queue
    cd persist-queue
    python setup.py install


Benchmark
---------

Here is the result for writing/reading **10000** items to the disk comparing the sqlite3 and file queue.

Environment:
    - OS: Windows 10
    - Disk: SATA3 SSD
    - RAM: 16 GiB

+---------+-----------------------+----------------+----------------------------+---------------------+
|         | Transaction write (s) | Bulk write (s) | Transaction write/read (s) | Bulk write/read (s) |
+---------+-----------------------+----------------+----------------------------+---------------------+
| SQLite3 | 64.98                 | 0.19           | 142.82                     | 63.82               |
+---------+-----------------------+----------------+----------------------------+---------------------+
| File    | 89.68                 | 85.78          | 101.37                     | 85.76               |
+---------+-----------------------+----------------+----------------------------+---------------------+

- **Transaction** refers to commit the change to disk on every write.
- **Bulk** refers to only commit the change to disk on last write.

To see the real performance on your host, run the script under `benchmark/run_benchmark.py`:

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


Tips
----
``task_done`` is required both for filed based queue and SQLite3 based queue (when ``auto_commit=False``)
to persist the cursor of next ``get`` to the disk.


Performance impact
------------------

- **WAL**

  Starting on v0.3.2, the `persistqueue` is leveraging the sqlite3 buildin feature
  `WAL <https://www.sqlite.org/wal.html>` which can improve the performance
  significantly, a general testing indicates that `persistqueue` is 2-4 times
  faster than previous version.

- **auto_commit=False**

  Since persistqueue v0.3.0, a new parameter ``auto_commit`` is introduced to tweak
  the performance for sqlite3 based queues as needed. When specify ``auto_commit=False``, user
  needs to perform ``queue.task_done()`` to persist the changes made to the disk since
  last ``task_done`` invocation.

Tests
-----

*persist-queue* use ``tox`` to trigger tests.

to trigger tests based on python2.7/python3.x, use:

.. code-block:: console

    tox -e py27

.. code-block:: console

    tox -e py34

.. code-block:: console

    tox -e py35

.. code-block:: console

    tox -e py36

to trigger pep8 check, use:

.. code-block:: console

   tox -e pep8


`pyenv <https://github.com/pyenv/pyenv>`_ is usually a helpful tool to manage multiple versions of Python.

Caution
-------

Currently, the atomic operation is not supported on Windows due to the limitation of Python's `os.rename <https://docs.python.org/2/library/os.html#os.rename>`_,
That's saying, the data in ``persistqueue.Queue`` could be in unreadable state when an incidental failure occurs during ``Queue.task_done``.

**DO NOT put any critical data on persistqueue.queue on Windows**.

Contribution
------------

Simply fork this repo and send PR for your code change(also tests to cover your change), remember to give a title and description of your PR. I am willing to
enhance this project with you :).


License
-------

`BSD <LICENSE>`_

FAQ
---

* ``sqlite3.OperationalError: database is locked`` is raised.

persistqueue open 2 connections for the db if ``multithreading=True``, the
SQLite database is locked until that transaction is committed. The ``timeout``
parameter specifies how long the connection should wait for the lock to go away
until raising an exception. Default time is **10**, increase ``timeout``
when creating the queue if above error occurs.
