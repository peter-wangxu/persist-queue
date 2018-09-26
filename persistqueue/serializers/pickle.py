#! coding = utf-8

"""A serializer that extends pickle to change the default protocol"""

from __future__ import absolute_import
from .. import common
import pickle

protocol = common.select_pickle_protocol()


def dump(value, fp):
    "Serialize value as pickle to a byte-mode file object"
    pickle.dump(value, fp, protocol=protocol)


def dumps(value):
    "Serialize value as pickle to bytes"
    return pickle.dumps(value, protocol=protocol)


def load(fp):
    "Deserialize one pickle value from a byte-mode file object"
    return pickle.load(fp)


def loads(bytes_value):
    "Deserialize one pickle value from bytes"
    return pickle.loads(bytes_value)
