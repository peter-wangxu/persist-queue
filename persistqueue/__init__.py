# coding=utf-8
__author__ = 'Peter Wang'
__license__ = 'BSD License'
__version__ = '0.2.0'


from .exceptions import Empty, Full  # noqa

from .queue import Queue  # noqa
from .sqlqueue import SQLiteQueue, FIFOSQLiteQueue, FILOSQLiteQueue  # noqa

__all__ = ["Queue", "SQLiteQueue", "FIFOSQLiteQueue", "FILOSQLiteQueue",
           "Empty", "Full", "__author__", "__license__", "__version__"]
