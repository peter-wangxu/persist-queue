#! coding = utf-8

"""
A serializer that extends msgpack to specify recommended parameters and adds a
4 byte length prefix to store multiple objects per file.
"""

from __future__ import absolute_import
import msgpack
import struct


def dump(value, fp):
    "Serialize value as msgpack to a byte-mode file object"
    packed = msgpack.packb(value, use_bin_type=True)
    length = struct.pack("<L", len(packed))
    fp.write(length)
    fp.write(packed)


def dumps(value):
    "Serialize value as msgpack to bytes"
    return msgpack.packb(value, use_bin_type=True)


def load(fp):
    "Deserialize one msgpack value from a byte-mode file object"
    length = struct.unpack("<L", fp.read(4))[0]
    return msgpack.unpackb(fp.read(length), use_list=False, raw=False)


def loads(bytes_value):
    "Deserialize one msgpack value from bytes"
    return msgpack.unpackb(bytes_value, use_list=False, raw=False)
