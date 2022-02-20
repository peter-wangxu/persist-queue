# coding=utf-8

import logging
import pickle

log = logging.getLogger(__name__)


def select_pickle_protocol():
    if pickle.HIGHEST_PROTOCOL <= 2:
        r = 2  # python2 use fixed 2
    else:
        r = 4  # python3 use fixed 4
    log.info("Selected pickle protocol: '{}'".format(r))
    return r
