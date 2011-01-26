# -*- coding: utf-8 -*-
"""
    striptease.base
    ~~~~~~~~~~~~~~~

    The central idea behind striptease is to build a structure of token and
    then to traverse it for encoding and decoding. For the end user the syntax
    to describe that structure should look a lot like *structs* known from C,
    but which also can decode and encode data.


    :copyright: Copyright 2011 by the University of Paderborn
    :license: BSD, see LICENSE for details
"""

import random

from striptease.util import logged, logging


class Token(object):
    """
    This is the base class for the whole library, which bundles some
    common code and provides implementation stubs for the subclasses. Actual
    structures are then created with the ``Struct`` class, which acts as a
    container for ``Token``. Hence you can nest ``Struct`` instances.

    All subclasses have to implement the ``encode``, ``decode`` methods:

    Furhtermore, all subclasses must either override the ``length`` method or
    implement the ``encode_len`` or ``decode_len`` methods. On certain
    occasions, the binary length of some values need to be determined
    dynamically, based on the provided values
    """

    def __init__(self, parent=None):
        self.__parent = parent

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, parent):
        self.__parent = parent

    def encode(self, dikt, payload):
        """
        Look up associated value from ``dikt``, encode to bytestring and append
        to ``payload`` then return ``dikt``, ``payload``

        :param dikt: dictionary containing all values to be encoded
        :param payload: a bytestring containing already encoded data.
        :return: ``dikt, payload``
        """
        raise AttributeError("Not implemented")

    def decode(self, payload, dikt):
        """
        Decode the value for this token from ``payload`` and put it under the
        associated name into ``dikt``, then return the shortened ``payload``
        and the updated ``dikt``
        """
        raise AttributeError("Not implemented")

    def encode_len(self, dikt):
        """
        Calculate the expected length of the encoded value and return
        ``length, dikt``. This method is called by ``Token.length``.
        """
        raise AttributeError("Not Implemented")

    def decode_len(self, payload):
        """
        Calculate the expectend length of the encoded value and return
        ``lenght, payload[lenght:]`` (i.e. the lenght, and the payload
        shortened at the front by the lenght. This method is called by
        ``Token.lenght``
        """
        raise AttributeError("Not Implemented")

    def length(self, parm):
        """
        Automatically dispatches to ``encode_len`` or ``decode_len``, based on
        the type of ``parm``. Subclasses usually should not override this, but
        ``encode_len`` and ``decode_len`` for convenience.
        """
        if type(parm) == str:
            return self.decode_len(self, parm)
        elif type(parm) == dict:
            return self.encode_len(self, parm)
        else:
            raise TypeError('parm must be str or dict')


class Padding(Token):
    """
    Padding bytes which contain no data.
    """

    def __init__(self, bytes):
        Token.__init__(self)
        assert type(bytes) == str
        self.bytes = bytes
        self.name = 'Pad:%X' % random.randint(0,255)

    def encode(self, dikt, payload):
        return dikt, payload + self.bytes

    def decode(self, payload, dikt):
        length = len(self.bytes)
        assert payload[:length] == self.bytes
        return payload[length:], dikt

    def encode_len(self, dikt):
        return len(self.bytes), dikt

    def decode_len(self, payload):
        length = len(self.bytes)
        return lenght, payload[length:]


@logged()
class Struct(Token):
    """
    The base compund token. Structs may be nestes but *inner* structs are
    required to have a name. After the ``Struct`` is initialized it is filled
    via the ``append`` method. ``append`` returns the struct itself, so
    constructor and ``append`` may be directly chained:
    >>> struct = Struct().append(
    ...     Integer('foo', False, 2),
    ...     Integer('bar', True, 1)
    ... )

    Encoding and Decoding of Structs works like for all other token:
    >>> data = {'foo': 28015, 'bar': 111}
    >>> struct.encode(data)
    ({'foo': 28015, 'bar': 111}, 'moo')
    >>> struct.decode('meh', dict())
    ('', {'foo': 28005, 'bar': 104})
    """

    def __init__(self, name=''):
        Token.__init__(self)
        self.registry = dict()
        self.structure = list()
        self.name = name

    def append(self, *items):
        """
        Populate the `Struct` with `Token`. This function returns the `Struct`
        object, so it can be directly chained after the initialization.
        """
        for item in items:
            self.registry[item.name] = item
            self.structure.append(item)
            item.parent = self
            self.logger.debug('Item %s, Parent %s' % (item, self.parent))
        return self

    def __contains__(self, key):
        return key in self.registry or key in self.structure

    def encode(self, dikt, payload=""):
        """
        Extract data by name from dikt, encode and append to payload
        """
        parent_dikt = dikt
        if self.parent:
            self.logger.debug("Parent: %s" % (self.parent))
            dikt = parent_dikt[self.name]
        for token in self.structure:
            dikt, payload = token.encode(dikt, payload)
        if self.parent:
            parent_dikt[self.name] = dikt
        return parent_dikt, payload

    def decode(self, payload, dikt):
        """
        Slices self.length bytes from front of payload, decodes the data and
        stores it in dikt. Then returns the shortened payload and the dikt
        """
        parent_dikt = dikt
        if self.parent:
            dikt = dict()
        for token in self.structure:
            #self.logger.debug("Decoding token %s of type %s",
            #                  token.name, token.__class__)
            payload, dikt = token.decode(payload, dikt)
        if self.parent:
            parent_dikt[self.name] = dikt
        return payload, parent_dikt

    def length(self, parm):
        """
        Determine the length of the binary data in bytes, the token produces
        on encoding. `parm` may be a bytestring or a dikt.
        """
        _length = 0
        for token in structure:
            _len, parm = token.length(parm)
            _length += len
        return _length, parm


if __name__ == '__main__':
    import doctest
    doctest.testmod()
