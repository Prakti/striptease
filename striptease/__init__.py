# -*- coding: utf-8 -*-
"""
    striptease
    ~~~~~~~~~~

    A library for encoding and decoding of binary data; the sexy way.

    :copyright: Copyright 2011 by the University of Paderborn
    :license: BSD, see LICENSE for details
"""

from striptease.base import Token, Padding, Struct
from striptease.numbers import Integer, Float
from striptease.sequences import Dynamic, Static, Consumer, Array, String, array_factory


class NumberFactory(object):
    """
    A factory class for creating convenient shorthand notations for number
    types parallel to C99 types. It also supports an array initializer
    notation.
    """

    def __init__(self, sign, length):
        self.sign = sign
        self.length = length

    def __call__(self, name, endian='!'):
        raise AttributeError("Subclass should implement this!")


class IntegerFactory(NumberFactory):
    """
    Factory class for C99 lookalike type-token, including array notations

    .. todo:: examples
    """

    def __init__(self, sign, length):
        NumberFactory.__init__(self, sign, length)

    def __call__(self, name, endian='!'):
        factory = array_factory(Integer)
        return factory(name, self.sign, self.length, endian)


class FloatFactory(NumberFactory):
    """
    Factory class for C99 float lookalike type-token, including array
    notations.

    .. todo:: examples
    """

    def __init__(self, length):
        if length != 4 and length != 8:
            raise ValueError("Floats can only have length 4 or 8")
        else: NumberFactory.__init__(self, True, length)

    def __call__(self, name, endian='!'):
        factory = array_factory(Float)
        return factory(name, self.length, endian)


for i in [1, 2, 4, 8]:
    # auto-generate shorthand factory's and inject into module namespace
    locals()['uint%d' % (i * 8)] = IntegerFactory(False, i)
    locals()['int%d' % (i * 8)] = IntegerFactory(True, i)

single = FloatFactory(4)
double = FloatFactory(8)

Bytes = String

Struct = array_factory(Struct)

try:
    from striptease.bitstring import Bitfield
except ImportError:
    pass # Ignore
