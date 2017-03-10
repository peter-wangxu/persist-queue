# coding=utf-8
__author__ = 'Peter Wang'
__license__ = 'BSD License'
__version__ = '0.1.6'


from .exceptions import Empty, Full # noqa

from .queue import Queue  # noqa

__all__ = ["Queue", "Empty", "Full", "__author__",
           "__license__", "__version__"]
