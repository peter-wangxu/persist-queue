#! coding = utf-8


class Empty(Exception):
    pass


class Full(Exception):
    pass


class MaxRetriesReached(Exception):
    def __init__(self, msg, orig_ex=None, *args, **kwargs):
        self.msg = msg
        self.orig_ex = orig_ex
        self.args = args
        self.kwargs = kwargs

    @property
    def message(self):
        msg = self.msg
        if self.args:
            msg = msg % self.args
        if self.kwargs:
            msg = msg.format(self.kwargs)

        if self.orig_ex:
            msg = msg + " Original exception: " + self.orig_ex
        return msg
