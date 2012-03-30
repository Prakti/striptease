# -*- coding: utf-8 -*-
"""
    striptease.numbers
    ~~~~~~~~~~~~~~~~~~

    Defines Tokens for handling numbers. The base-implementations of this
    module heavily rely on the std-lib module struct for de-/encoding python
    numbers into and out of bytestrings. This module just harbors the basic
    implementations for maximum flexibility, but not the definition of the
    shorthand notations.

    :copyright: Copyright 2011 by the University of Paderborn
    :license: BSD, see LICENSE for details
"""


import struct

from striptease.base import Token


class Number(Token):
    """
    Abstract Base class for encoding numbers. Subclasses must define ``FMT``
    for resolving format strings from sizes. This class should not be
    instantiated, it just accumulates common code parts for the
    :py:class:`.Integer` and :py:class:`.Float` class.

    :param name: the name under which the token should look up or store its
                 value during en-/decoding.
    :param sign: ``True`` if this is a signed number, defaults to ``True`` for
                 all floating point numbers.
    :param length: the length in bytes of the number. Is used to look up the
                   correct format string from the ``FMT`` dict, the subclasses
                   must supply.
    :param endian: you can specify byte-endianness like defined in the
                   :py:mod:`struct` module, default is '!'
    """

    def __init__(self, name, sign, length, endian='!'):
        Token.__init__(self)
        assert endian in '@ = < > !'.split()
        self.name = name
        self.sign = sign
        self.__length = length
        self.endian = endian

    def fmt(self):
        """
        Looks up the format-string of the  according to the specified length.

        .. todo:: Better explanation of interaction with subclasses
        """
        fmt = self.FMT[self.__length]
        return self.endian + (fmt if self.sign else fmt.upper())

    def encode(self, dikt, payload=""):
        """
        Lookup the value to be encoded via `self.name` from dikt, encode to
        binary and append to payload.
        """
        return dikt, payload + struct.pack(self.fmt(), dikt[self.name])

    def decode(self, payload, dikt):
        """
        Slices self.__length bytes from front of payload, decodes the data and
        stores it in dikt. Then returns the shortened payload and the dikt
        """
        data, payload = payload[:self.__length],payload[self.__length:]
        values = struct.unpack(self.fmt(), data)
        dikt[self.name] = values[0]
        return payload, dikt

    def encode_len(self, dikt):
        return self.__length, dikt

    def decode_len(self, payload):
        return self.__length, payload[self.__length:]


class Integer(Number):
    """
    Subclass of :py:class:`.Nunber` for handling integer numbers. Inherits
    :py:meth:`encode` and :py:meth:`decode` from :py:class:`.Number` and
    defines ``FMT`` as a lookup table for the correct format specifier used in
    :py:class:`.Number`.

    :param lenght: may be 1, 2, 4, or 8.

    Example:

    >>> int16_token = Integer('foo', True, 2)
    >>> data = {'foo' : 25976}
    >>> int16_token.encode(data)
    ({'foo': 25976}, 'ex')
    >>> bytes = 'AB'
    >>> int16_token.decode(bytes, dict())
    ('', {'foo': 16706})
    """

    FMT = {
        1 : 'b',
        2 : 'h',
        4 : 'i',
        8 : 'q',
    }

    def __init__(self, name, sign, length, endian='!'):
        Number.__init__(self, name, sign, length, endian)
        self.array_name = None


class Float(Number):
    """
    Subclass of Number for handling floating-point numbers. Similar to
    :py:class:`.Integer`, this class also does not implement own :py:meth:`encode` and
    :py:meth:`decode` methods but defines ``FMT``.

    :param lenght: may be 4 or 8, for single or double precision respectively.

    Example:

    >>> from striptease import Float
    >>> single_token = Float('bar', 4)
    >>> data = {'bar': 4.359794990231121e+27}
    >>> single_token.encode(data)
    ({'bar': 4.359794990231121e+27}, 'maeh')
    >>> bytes = 'moep'
    >>> single_token.decode(bytes, dict())
    ('', {'bar': 4.6305967350080394e+27})
    """

    FMT = {
        4 : 'f',
        8 : 'd',
    }

    def __init__(self, name, length, endian='!'):
        Number.__init__(self, name, True, length, endian)


