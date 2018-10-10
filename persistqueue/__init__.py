# coding=utf-8
__author__ = 'Peter Wang'
__license__ = 'BSD'
__version__ = '0.4.1'

from .exceptions import Empty, Full  # noqa
from .queue import Queue  # noqa
try:
    from .pdict import PDict  # noqa
    from .sqlqueue import SQLiteQueue, FIFOSQLiteQueue, FILOSQLiteQueue, UniqueQ  # noqa
    from .sqlackqueue import SQLiteAckQueue
except ImportError as error:
    pass

__all__ = ["Queue", "SQLiteQueue", "FIFOSQLiteQueue", "FILOSQLiteQueue",
           "UniqueQ", "PDict", "SQLiteAckQueue", "Empty", "Full",
           "__author__", "__license__", "__version__"]
