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
    This is the base class for the whole library, which bundles some common
    code and provides implementation stubs for the subclasses. Actual
    structures are then created with the :py:class:`.Struct` class, which acts
    as a container for :py:class:`Token`. Hence you can nest
    :py:class:`.Struct` instances.

    All subclasses  of :py:class:`!Token` have to implement the methods
    :py:meth:`encode <.Token.encode>` and :py:meth:`decode <.Token.decode>`

    Furhtermore, all subclasses must either override the :py:meth:`length
    <.Token.length>` method or implement the :py:meth:`encode_len
    <.Token.encode_len>` or :py:meth:`decode_len <.Token.decode_len>` methods.
    On certain occasions, the binary length of some values need to be
    determined dynamically, based on the provided values
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

        :return: the ``dikt`` and the extended ``payload``
        """
        raise AttributeError("Not implemented")

    def decode(self, payload, dikt):
        """
        Decode the value for this token from ``payload`` and put it under the
        associated name into ``dikt``, then return the shortened ``payload``
        and the updated ``dikt``. It is important that decoded data is
        stripped from the front of ``payload``, so the next token knows where
        to start decoding.

        :param payload: a bytestring containing the data to decode.
        :param dikt: a dictionary where the decoded data is stored under the
                     token's name
        :return: the ``dikt`` containing the decoded values and the shortened
                     ``payload``
        """
        raise AttributeError("Not implemented")

    def encode_len(self, dikt):
        """
        Calculate the expected length of the encoded value and return
        ``length, dikt``. This method is called by :py:meth:`length
        <.Token.length>`.
        """
        raise AttributeError("Not Implemented")

    def decode_len(self, payload):
        """
        Calculate the expectend length of the encoded value and return
        ``lenght, payload[lenght:]`` (i.e. the lenght, and the payload
        shortened at the front by the lenght. This method is called by
        :py:meth:`length <.Token.length>`
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
    Padding bytes which contain no actual data. ``bytes`` has to be a
    bytestring representation which can be inlined into the payload.
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
    The base compund token. Structs may be nested but *inner* structs are
    required to have a name. After the :py:class:`.Struct` is initialized it
    is populated with sub-token via the :py:meth:`.append` method.
    :py:meth:`.append` returns the struct itself, so constructor and
    :py:meth:`.append` may be directly chained:

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

    :param name: (optional) used to store and retrieve data from the supplied
                 dictonary during de- and encoding
    """

    def __init__(self, name=""):
        Token.__init__(self)
        self.registry = dict()
        self.structure = list()
        self.name = name

    def append(self, *items):
        """
        Populate the :py:class:`.Struct` with :py:class:`.Token`. This function returns the
        :py:class:`.Struct` object, so it can be directly chained after the
        initialization. This method accepts an arbitrary number of arguments,
        all of which must be subclasses of :py:class:`.Token`.
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
        Iterates over all tokens in the structure and encode the data from
        ``dikt`` and append it to ``payload``. Returns ``dikt`` as is and
        and the initial ``payload`` plus the encoded data.
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
        Iterates over all tokens in the structure and successively decodes
        their values from ``payload`` into ``dikt``, thereby consuming
        ``payload``. Returns the initial ``payload`` minus the decoded data.
        If necessary, you have to manually preserve ``payload`` before handing
        it to ``decode``.
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
        Computes the length of the struct in bytes, based on the information
        in ``parm``. Parm can be either ``payload`` or ``dikt``
        """
        _length = 0
        for token in structure:
            _len, parm = token.length(parm)
            _length += len
        return _length, parm


if __name__ == '__main__':
    import doctest
    doctest.testmod()
