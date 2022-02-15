# coding=utf-8
try:
    from queue import (
        Empty as StdEmpty,
        Full as StdFull
    )
except ImportError:
    from Queue import (
        Empty as StdEmpty,
        Full as StdFull
    )


class Empty(StdEmpty):
    pass


class Full(StdFull):
    pass
