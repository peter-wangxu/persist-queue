__author__ = 'Peter Wang'
__license__ = 'BSD'
__version__ = '1.0.0'

# Relative imports assuming the current package structure
from .exceptions import Empty, Full  # noqa: F401
from .queue import Queue  # noqa: F401
import logging
log = logging.getLogger(__name__)

# Attempt to import optional components, logging if not found.
try:
    from .pdict import PDict  # noqa: F401
    from .sqlqueue import (  # noqa: F401
        SQLiteQueue,
        FIFOSQLiteQueue,
        FILOSQLiteQueue,
        UniqueQ
    )
    from .sqlackqueue import (  # noqa: F401
        SQLiteAckQueue,
        FIFOSQLiteAckQueue,
        FILOSQLiteAckQueue,
        UniqueAckQ,
        AckStatus
    )
except ImportError:
    # If sqlite3 is not available, log a message.
    log.info("No sqlite3 module found, sqlite3 based queues are not available")

try:
    from .mysqlqueue import MySQLQueue  # noqa: F401
except ImportError:
    # failed due to DBUtils not installed via extra-requirements.txt
    log.info("DBUtils may not be installed, install "
             "via 'pip install persist-queue[extra]'")

# Define what symbols are exported by the module.
__all__ = [
    "Queue",
    "SQLiteQueue",
    "FIFOSQLiteQueue",
    "FILOSQLiteQueue",
    "UniqueQ",
    "PDict",
    "SQLiteAckQueue",
    "FIFOSQLiteAckQueue",
    "FILOSQLiteAckQueue",
    "UniqueAckQ",
    "AckStatus",
    "MySQLQueue",
    "Empty",
    "Full",
    "__author__",
    "__license__",
    "__version__"
]
