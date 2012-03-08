# -*- coding: utf-8 -*-
"""
    striptease.util
    ~~~~~~~~~~~~~~~

    Utility module for striptease.
"""

try:
    import logbook as logging
    Logger = logging.Logger
except ImportError:
    import logging
    def Logger(name, level=None):
        """
        This is a function that emulates the logbook Logger constructor
        """
        logger = logging.getLogger(name)
        if level:
            logger.setLevel(level)
        return logger



class logged(object):
    """
    A decorator for injecting a logger into classes.
    """

    def __init__(self, disable=False, level=logging.INFO):
        self.disable=disable
        self.level=level

    def __call__(self, cls):
        if self.disable:
            cls.logger = VoidLogger()
        else:
            cls.logger = Logger('%s.%s' % (cls.__module__, cls.__name__),
                                level=self.level)
        return cls


class VoidLogger(object):
    """
    A catchall logger for directing all logging messages into the void.
    Used to completely disable logging for a class.
    """
    debug = info = warn = warning = notice = error = exception = \
            critical = log = lambda *args, **kwargs: None


if __name__ == '__main__':
    @logged(level=DEBUG)
    class A(object):
        pass
    a = A()
    a.logger.debug("Foo!")
    @logged(disable=True)
    class B(object):
        pass
    b = B()
    b.logger.debug("Foo!")

