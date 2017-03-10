# coding=utf-8

"""A single process, persistent multi-producer, multi-consumer queue."""

import os
import pickle
import tempfile

import threading
from time import time as _time
from persistqueue.exceptions import Empty, Full


def _truncate(fn, length):
    with open(fn, 'ab+') as f:
        f.truncate(length)


class Queue(object):
    def __init__(self, path, maxsize=0, chunksize=100, tempdir=None):
        """Create a persistent queue object on a given path.

        The argument path indicates a directory where enqueued data should be
        persisted. If the directory doesn't exist, one will be created.
        If maxsize is <= 0, the queue size is infinite. The optional argument
        chunksize indicates how many entries should exist in each chunk file on
        disk.

        The tempdir parameter indicates where temporary files should be stored.
        The tempdir has to be located on the same disk as the enqueued data in
        order to obtain atomic operations.
        """
        self.path = path
        self.chunksize = chunksize
        self.tempdir = tempdir
        self.maxsize = maxsize
        self._init(maxsize)
        if self.tempdir:
            if os.stat(self.path).st_dev != os.stat(self.tempdir).st_dev:
                raise ValueError("tempdir has to be located "
                                 "on same path filesystem")
        self.info = self._loadinfo()
        # truncate head case it contains garbage
        hnum, hcnt, hoffset = self.info['head']
        headfn = self._qfile(hnum)
        if os.path.exists(headfn):
            if hoffset < os.path.getsize(headfn):
                _truncate(headfn, hoffset)
        # let the head file open
        self.headf = self._openchunk(hnum, 'ab+')
        # let the tail file open
        tnum, _, toffset = self.info['tail']
        self.tailf = self._openchunk(tnum)
        self.tailf.seek(toffset)
        # update unfinished tasks with the current number of enqueued tasks
        self.unfinished_tasks = self.info['size']
        # optimize info file updates
        self.update_info = True

    def _init(self, maxsize):
        self.mutex = threading.Lock()
        self.not_empty = threading.Condition(self.mutex)
        self.not_full = threading.Condition(self.mutex)
        self.all_tasks_done = threading.Condition(self.mutex)

        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def join(self):
        with self.all_tasks_done:
            while self.unfinished_tasks:
                self.all_tasks_done.wait()

    def qsize(self):
        n = None
        with self.mutex:
            n = self._qsize()
        return n

    def _qsize(self):
        return self.info['size']

    def put(self, item, block=True, timeout=None):
        "Interface for putting item in disk-based queue."
        self.not_full.acquire()
        try:
            if self.maxsize > 0:
                if not block:
                    if self._qsize() == self.maxsize:
                        raise Full
                elif timeout is None:
                    while self._qsize() == self.maxsize:
                        self.not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    endtime = _time() + timeout
                    while self._qsize() == self.maxsize:
                        remaining = endtime - _time()
                        if remaining <= 0.0:
                            raise Full
                        self.not_full.wait(remaining)
            self._put(item)
            self.unfinished_tasks += 1
            self.not_empty.notify()
        finally:
            self.not_full.release()

    def _put(self, item):
        pickle.dump(item, self.headf)
        self.headf.flush()
        hnum, hpos, _ = self.info['head']
        hpos += 1
        if hpos == self.info['chunksize']:
            hpos = 0
            hnum += 1
            self.headf.close()
            self.headf = self._openchunk(hnum, 'ab+')
        self.info['size'] += 1
        self.info['head'] = [hnum, hpos, self.headf.tell()]
        self._saveinfo()

    def put_nowait(self, item):
        return self.put(item, False)

    def get(self, block=True, timeout=None):
        self.not_empty.acquire()
        try:
            if not block:
                if not self._qsize():
                    raise Empty
            elif timeout is None:
                while not self._qsize():
                    self.not_empty.wait()
            elif timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")
            else:
                endtime = _time() + timeout
                while not self._qsize():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
            item = self._get()
            self.not_full.notify()
            return item
        finally:
            self.not_empty.release()

    def get_nowait(self):
        return self.get(False)

    def _get(self):
        tnum, tcnt, toffset = self.info['tail']
        hnum, hcnt, _ = self.info['head']
        if [tnum, tcnt] >= [hnum, hcnt]:
            return None
        data = pickle.load(self.tailf)
        toffset = self.tailf.tell()
        tcnt += 1
        if tcnt == self.info['chunksize'] and tnum <= hnum:
            tcnt = toffset = 0
            tnum += 1
            self.tailf.close()
            os.remove(self.tailf.name)
            self.tailf = self._openchunk(tnum)
        self.info['size'] -= 1
        self.info['tail'] = [tnum, tcnt, toffset]
        self.update_info = True
        return data

    def task_done(self):
        with self.all_tasks_done:
            unfinished = self.unfinished_tasks - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError("task_done() called too many times.")
                self.all_tasks_done.notify_all()
            self.unfinished_tasks = unfinished
            self._task_done()

    def _task_done(self):
        if self.update_info:
            self._saveinfo()
            self.update_info = False

    def _openchunk(self, number, mode='rb'):
        return open(self._qfile(number), mode)

    def _loadinfo(self):
        infopath = self._infopath()
        if os.path.exists(infopath):
            with open(infopath, 'rb') as f:
                info = pickle.load(f)
        else:
            info = {
                'chunksize': self.chunksize,
                'size': 0,
                'tail': [0, 0, 0],
                'head': [0, 0, 0],
            }
        return info

    def _gettempfile(self):
        if self.tempdir:
            return tempfile.mkstemp(dir=self.tempdir)
        else:
            return tempfile.mkstemp()

    def _saveinfo(self):
        tmpfd, tmpfn = self._gettempfile()
        os.write(tmpfd, pickle.dumps(self.info))
        os.close(tmpfd)
        # POSIX requires that 'rename' is an atomic operation
        try:
            os.rename(tmpfn, self._infopath())
        except OSError as e:
            if getattr(e, 'winerror', None) == 183:
                os.remove(self._infopath())
                os.rename(tmpfn, self._infopath())
            else:
                raise e

    def _qfile(self, number):
        return os.path.join(self.path, 'q%05d' % number)

    def _infopath(self):
        return os.path.join(self.path, 'info')
