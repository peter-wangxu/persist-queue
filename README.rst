persist-queue - A thread-safe, disk-based queue for Python
==========================================================

.. image:: https://img.shields.io/circleci/project/github/peter-wangxu/persist-queue.svg?label=Linux%20%26%20Mac
    :target: https://github.com/peter-wangxu/persist-queue

.. image:: https://img.shields.io/appveyor/ci/peter-wangxu/persist-queue.svg?label=Windows
    :target: https://github.com/peter-wangxu/persist-queue

.. image:: https://img.shields.io/codecov/c/github/peter-wangxu/persist-queue.svg
    :target: https://github.com/peter-wangxu/persist-queue

.. image:: https://img.shields.io/pypi/v/persist-queue.svg
    :target: https://pypi.python.org/pypi/persist-queue

This project is based on the achievements of `python-pqueue <https://github.com/balena/python-pqueue>`_
and `queuelib <https://github.com/scrapy/queuelib>`_

The goals is to achieve following requirements:

* Disk-based: each queued item should be stored in disk in case of any crash.
* Thread-safe: can be used by multi-threaded producers and multi-threaded consumers.
* Recoverable: Items can be read after process restart.
* Green-compatible: It can be used in ``greenlet`` or ``eventlet`` environment.

While *queuelib* and *python-pqueue* cannot fulfil all of above. After some try, I found it's hard to achieve based on their current
implementation without huge code change. this is the motivation to start this project.

Besides, *persist-queue* can serialize any object instances supported by python *pickle* object serialization module.
To support customized objects, please refer to `Pickling and unpickling extension types(Python2) <https://docs.python.org/2/library/pickle.html#pickling-and-unpickling-normal-class-instances>`_
and `Pickling Class Instances(Python3) <https://docs.python.org/3/library/pickle.html#pickling-class-instances>`_

Requirements
------------
* Python 2.7 or Python 3.x.
* Fully support for Linux and Windows.

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


Examples
--------

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

example usage with multi-thread(referred from github project python-pqueue):

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


Tests
-----

*persist-queue* use ``tox`` to trigger tests.

to trigger tests based on python2.7/python3.4/python3.5, use:

.. code-block:: console

    tox -e py27

.. code-block:: console

    tox -e py34

.. code-block:: console

    tox -e py35


to trigger pep8 check, use:

.. code-block:: console

   tox -e pep8


Contribution
------------

Simply fork this repo and send PR for your code change(also tests to cover your change), remember to give a title and description of your PR. I am willing to
enhance this project with you :).


License
-------

`Apache License Version 2.0 <LICENSE>`_


FAQ
---


