import logging
import re
import time as _time

from persistqueue.exceptions import MaxRetriesReached

log = logging.getLogger(__name__)


def retrying(error_clz, msg=None, max=3):
    """Retry decorator for error.

    :param error_clz: exception for retry.
    :param msg: optional exception message for retry.
    :param max: max retry count.
    """
    # TODO support both @retrying and @retry() as valid syntax
    def retry(func):
        def wrapper(*args, **kwargs):
            i = 0
            while i <= max:
                i += 1  # remember execution count
                try:
                    return func(*args, **kwargs)
                except Exception as ex:
                    retry = _retry_on_exception(ex, error_clz, msg)
                    if retry:
                        _raise_if_max_reached(i, max, ex)
                        log.warning("Retrying on error '%s', left retries: "
                                    "%d", ex, max-i)
                        _time.sleep(i**2 * 0.1)
                    else:
                        raise
        return wrapper
    return retry


def _raise_if_max_reached(i, max, ex):
    if i >= max:
        raise MaxRetriesReached('Max retries reached.', orig_ex=ex)


def _retry_on_exception(error, error_clz, msg):
    retry = False
    if isinstance(error, error_clz):
        if msg:
            if re.search(msg, str(error)):
                retry = True
            else:
                log.debug("exception '%s' occurred, "
                          "but message did not match, "
                          "found: '%s'", error_clz, str(error))
                retry = False
        else:
            retry = True
    else:
        log.debug("exception '%s' occurred, but type did not match, "
                  "found: '%s'", type(error), error_clz)
    return retry
