#! coding = utf-8

"""
A serializer that extends json to use bytes and uses newlines to store
multiple objects per file.
"""

from __future__ import absolute_import
import json


def dump(value, fp, sort_keys=False):
    "Serialize value as json line to a byte-mode file object"
    fp.write(json.dumps(value, sort_keys=sort_keys).encode())
    fp.write(b"\n")


def dumps(value, sort_keys=False):
    "Serialize value as json to bytes"
    return json.dumps(value, sort_keys=sort_keys).encode()


def load(fp):
    "Deserialize one json line from a byte-mode file object"
    return json.loads(fp.readline().decode())


def loads(bytes_value):
    "Deserialize one json value from bytes"
    return json.loads(bytes_value.decode())
