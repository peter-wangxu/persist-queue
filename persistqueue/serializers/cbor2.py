# coding=utf-8

"""
A serializer that extends cbor2 to specify recommended parameters and adds a
4 byte length prefix to store multiple objects per file.
"""

from __future__ import absolute_import
try:
    import cbor2
except ImportError:
    pass

from struct import Struct


length_struct = Struct("<L")


def dump(value, fp, sort_keys=False):
    "Serialize value as cbor2 to a byte-mode file object"
    if sort_keys and isinstance(value, dict):
        value = {key: value[key] for key in sorted(value)}
    packed = cbor2.dumps(value)
    length = length_struct.pack(len(packed))
    fp.write(length)
    fp.write(packed)


def dumps(value, sort_keys=False):
    "Serialize value as cbor2 to bytes"
    if sort_keys and isinstance(value, dict):
        value = {key: value[key] for key in sorted(value)}
    return cbor2.dumps(value)


def load(fp):
    "Deserialize one cbor2 value from a byte-mode file object"
    length = length_struct.unpack(fp.read(4))[0]
    return cbor2.loads(fp.read(length))


def loads(bytes_value):
    "Deserialize one cbor2 value from bytes"
    return cbor2.loads(bytes_value)
