# -*- coding: utf-8 -*-
"""
    striptease.sequences
    ~~~~~~~~~~~~~~~~~~~~

    Token for creating sequences i.e. arrays of binary data. Two `Sequence`
    token are provided: `Array` and `String`. Each sequence token must be
    wrapped by a subclass of the `LengthSpecifier` type.

    :copyright: Copyright 2011 by the University of Paderborn
    :license: BSD, see LICENSE for details
"""

import struct

from striptease.base import Token, Struct
from striptease.util import logged


class LengthSpecifier(Token):
    """
    Abstract base class of all LengthSpecifier token.
    Three sub-classes are predefined, which are needed to determine the
    length of the binary data during encoding and decoding:

    :py:class:`.Static`:
            The size of the array or string is fixed

    :py:class:`.Dynamic`:
            The size of the array or string is determined by an integer number
            preceding the array or string

    :py:class:`.Consumer`:
            No size is given. When decoding, the Consumer takes all the
            remaining binary data and tries to decode it.

    """

    def __init__(self, seqtype):
        Token.__init__(self)
        self.seqtype = seqtype

    @property
    def name(self):
        return self.seqtype.name


class Static(LengthSpecifier):
    """
    Used to specify :py:class:`Sequences <.Sequence>` whose length is known at compile-time.

    :param length: must be an integer value, determines the lenght in
                   *elements*, similar to C arrays, not in bytes.
    :param seqtype: instance of a subclass of :py:class:`.Sequence`.
    """

    def __init__(self, length, seqtype):
        LengthSpecifier.__init__(self, seqtype)
        self.length = length

    def encode(self, dikt, payload=""):
        """
        Extract data by name from dikt, encode and append to payload
        """
        return self.seqtype.encode(self.length, dikt, payload)

    def decode(self, payload, dikt):
        """
        Slice self.length * self.atype.length bytes from front of payload,
        decodes the data and stores it as a tuple in dikt. Then returns the
        shortened payload and the dikt
        """
        return self.seqtype.decode(self.length, payload, dikt)

    def lenght(self, parm):
        return self.seqtype.length(self.length, parm)


class Dynamic(LengthSpecifier):
    """
    Used to specify :py:class:`Sequences <.Sequence>` whose length is specified in the bytestream.
    This length-field must precede the sequence data in the bytestream but
    does not have to do so diretly, i.e. other data may be in between the
    length-field and the actual sequence.

    .. todo:: examples for length fields

    :param len_name: is the name of the token specifying the length of the
                     sequence
    :param seqtype:  is the instance of a subclass of :py:class:`.Sequence`
    :param comp_len: (optional) is a function which should be used to count
                     the number of items in the value supplied by the
                     dictionary during encoding.
                     Defaults to :py:func:`len`
    """

    def __init__(self, len_name, seqtype, comp_len=len):
        self.len_name = len_name
        self.comp_len = comp_len
        self.__parent = None
        self.decoded_len = 0
        LengthSpecifier.__init__(self, seqtype)

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, parent):
        """
        When a :py:class:`.Struct` registers itself as a parent, we look up the token
        encoding our length and mokey-patch it's :py:meth:`encode` method. That way,
        the length of the dynamic array can be determined on the fly during
        encoding.

        Analogous, the lenght-token's :py:meth:`decode_len` method is patched, since
        this class' :py:meth:`decode_len` method needs the length information from
        the lenght-token.
        """
        if parent != None and type(parent) == Struct:
            self.__parent = parent
            length_token = parent.registry[self.len_name]

            # patch the encode-method of length-token
            self.sub_encode = length_token.encode
            length_token.encode = self.length_token__encode

            # patch the decode_len-method of length-token
            self.sub_decode_len = length_token.decode_len
            length_token.decode_len = self.length_token__decode_len
        else:
            pass # TODO: raise Exception


    def length_token__encode(self, dikt, payload=""):
        """ This is for patching the length-token's encode method """
        dikt[self.len_name] = self.comp_len(dikt[self.seqtype.name])
        return self.sub_encode(dikt, payload)

    def length_token__decode_len(self, payload):
        """ This is for patching the decode_len method of the length-token """
        length_token = self.parent[self.len_name]
        _payload = str(payload)
        _payload, dikt = length_token.decode(_payload, dict())
        self.decoded_len = dikt[self.len_name]
        return self.sub_decode_len(payload)

    def encode(self, dikt, payload=""):
        """ Determine length and dispatch to sequence token """
        length = self.comp_len(dikt[self.seqtype.name])
        return self.seqtype.encode(length, dikt, payload)

    def decode(self, payload, dikt):
        """ look up length and dispatch to sequence token """
        length = dikt[self.len_name]
        return self.seqtype.decode(length, payload, dikt)

    def encode_len(self, dikt):
        """ compute length and dispatch to sequence token """
        length = self.comp_len(dikt[self.seqtype.name])
        return self.seqtype.length(length, dikt)

    def decode_len(self, payload):
        """
        The patched ``decode_len`` method of the length-token, should have
        stored the length in this token's ``decoded_len`` attribute.
        """
        return self.seqtype.length(self.decoded_len, payload)


class Consumer(LengthSpecifier):
    """
    This :py:class:`.LengthSpecifier` is used for blob-like objects, i.e.:
    when you want to encode sequences of arbitrary size, without specifying an
    actual length.  When decoding, the :py:class:`.Consumer` tells its
    :py:class:`.Sequence` to try and decode all remaining binary data.

    .. warning::
        :py:class:`.Consumer` tell their sequences that they must decode until
        no more bytes are left in the payload. That why, sequences must be
        the last token in a struct. They may not work in combination with
        nested :py:class:`Structs <.Struct>`, because it is difficult to determine
        their length.
    """

    def __init__(self, seqtype):
        LengthSpecifier.__init__(self, seqtype)

    @property
    def name(self):
        return self.seqtype.name

    def encode(self, dikt, payload=""):
        return self.seqtype.encode(-1, dikt, payload)

    def decode(self, payload, dikt):
        return self.seqtype.decode(-1, payload, dikt)

    def encode_len(self, dikt):
        return self.seqtype.length(-1, dikt)

    def decode_len(self, payload):
        pass


class Sequence(Token):
    """
    Abstract base class for all sequence token. Overwrites the methods
    :py:meth:`.Token.length`, :py:meth:`.Token.encode_len` and
    :py:meth:`.Token.decode_len`.
    """

    def __init__(self):
        Token.__init__(self)

    def encode(self, length, dikt, payload=""):
        """
        Extends :py:meth:`.Token.encode` by requiring ``length`` as a
        parameter.

        :param length: the length of the sequence data from ``dikt`` to be
                       encoded into the ``payload``

                       .. note::
                            similar to arrays in C, the length does not
                            specify the length in bytes but `elements` of the
                            given type.

        :returns: ``dikt`` and the extended ``payload``
        """
        raise AttributeError("Not implemented")

    def decode(self, length, dikt, payload=""):
        """
        Extends :py:meth:`.Token.decode` by requiring ``length`` as a
        parameter.

        :param length: the length of the sequence data encoded in ``payload``
                       to be decoded into ``dikt``.

                       .. note::
                            similar to arrays in C, the length does not
                            specify the length in bytes but `elements` of the
                            given type.
        :return: the shortened ``payload`` and the ``dikt`` containing the
                  decoded data
        """
        raise AttributeError("Not implemented")

    def encode_len(self, lenght, dikt):
        """
        Extends :py:meth:`.Token.encode_len` by requireing ``length`` as a
        parameter. :py:meth:`.Sequence.length` dispatches to this method when
        the length in bytes is needed during encoding into ``payload``

        :param length: the length of the sequence in `elements`
        :return: the length of the encoded sequence in `bytes`
        """
        raise AttributeError("Not implemented")

    def decode_len(self, length, payload):
        """
        Extends :py:meth:`.Token.decode_len` by requiring ``length`` as a
        parameter. :py:meth:`.Sequence.length` dispatches to this method when
        the length in bytes is needed during decoding a ``payload``

        :param length: the length of the sequence in `elements`
        :return: the length of the encoded sequence in `bytes`
        """
        raise AttributeError("Not implemented")

    def length(self, length, parm):
        """
        Extends :py:meth:`.Token.length` by requiring ``length`` as a
        parameter. This method computes the actual length in bytes.

        :param length: the length of the sequence in `elements`
        :returns: the length of the encoded data in `bytes`
        """
        if type(parm) == str:
            return self.decode_len(length, parm)
        elif type(parm) == dict:
            return self.encode_len(length, parm)
        else:
            raise TypeError('parm must be of str or dict')


@logged()
class Array(Sequence):
    """
    This token is used to specify an array of a given type. After
    initialization, you must specify the type of the array via the
    :py:meth:`of <.Array.of>` method, which returns ``self``, so you can chain
    instantiation and array-type specification in one go.

    .. todo:: example for `of`
    """

    def __init__(self, name, reverse=False):
        Sequence.__init__(self)
        self.name = name
        self.reverse = reverse
        self.atype = None

    def of(self, atype):
        """
        This method is used to specify the type of the array.

        :param atype: a subclass of :py:class:`.Token` specifying the type of
                      the array
        :returns: ``self`` i.e.: the instance of :py:class:`.Array` on which
                  this method was called
        """
        self.atype = atype
        self.atype.parent = self
        return self

    def encode(self, length, dikt, payload=""):
        """
        Extract data by name from dikt, encode and append to payload.
        """
        data = dikt[self.name]
        if self.reverse:
            data = tuple(reversed(data))
        if length != -1:
            assert len(data) == length
        for i, d in enumerate(data):
            self.atype.name = i
            data, payload = self.atype.encode(data, payload)
        return dikt, payload

    def consume(self, payload, dikt):
        """
        Try and decode all of the remaining payload. This method is used in
        the case an Array is with a :py:class:`.Consumer` length-specifier.
        """
        array = []
        buf = dict()
        self.atype.name = self.name + '__buf'
        while payload:
            payload, buf = self.atype.decode(payload, buf)
            array.extend(buf.values())
        dikt[self.name] = array
        return payload, dikt

    def extract(self, length, payload, dikt):
        """
        Slice ``length * self.atype.length`` bytes from front of payload,
        decodes the data and stores it as a tuple in dikt. Then returns the
        shortened payload and the dikt
        """
        array = [None] * length
        for i in range(length):
            self.atype.name = i
            self.logger.debug("Array type: %s, Name: %s" % (self.atype, self.atype.name))
            payload, array = self.atype.decode(payload, array)
        if self.reverse:
            array = list(reversed(array))
        dikt[self.name] = array
        return payload, dikt

    def decode(self, length, payload, dikt):
        """
        For readability reaseons this method dispatches to two other methods,
        based on the wrapping :py:class:`.LengthSpecifier`

        :py:meth:`consume <.Array.consume>`:
                in case the wrapping length-specifier is a :py:class:`.Consumer` and
                hands over a length of -1

        :py:meth:`extract <.Array.extract>`:
                in case the wrapping length-specifier can supply an actual
                length.
        """
        if length == -1:
            return self.consume(payload, dikt)
        else:
            return self.extract(length, payload, dikt)

    def atype_length(self, parm):
        """
        Convenience wrapper for accessing the length of the array-type.
        Dispatches to :py:meth:`self.atype.length <.Token.length>`
        """
        _len, _parm = self.atype.length(parm)
        return _len

    def encode_len(self, length, dikt):
        if lenght == -1: # consumer case
            data = dikt[self.name]
            return len(data) * self.atype_length(dikt), dikt
        else:
            return length * self.atype_length(dikt), dikt

    def decode_len(self, length, payload):
        if length == -1: # consumer case
            return len(payload), ""
        else:
            _length, _parm = self.atype.length(parm)
            _length = length * _length
            return _lenght, payload[_length:]


@logged()
class String(Sequence):
    """
    Class for encoding bytestrings into a payload.

    :param name: the token's name. Used for retrieving and storing data from
                 the supplied dictionary during en- and decoding
    :param reverse: (optional) states if the values have to be reversed before
                    encoding and after decoding. This can be helpful if you
                    have sequences whose direction have a semantic but, for
                    mysterious reasons, are encoded reverse to that semantic
                    direction. defaults to ``False``
    """

    def __init__(self, name, endian='!', reverse=False):
        Sequence.__init__(self)
        self.name = name
        self.endian = endian
        self.reverse = reverse

    def encode(self, length, dikt, payload=""):
        """
        Extract data by name from dikt, encode and append to payload
        """
        value = dikt[self.name]
        if length == -1: # consumer case
            length = len(value)
        else:
            value = value[:length]
        if self.reverse:
            value = "".join(reversed(value))
        payload += struct.pack('%ds' % length, value)
        return dikt, payload

    def decode(self, length, payload, dikt):
        """
        TODO: document
        """
        if length == -1: # consumer case
            if self.reverse:
                value = "".join(reversed(payload))
            else:
                value = payload
            dikt[self.name] = value
            payload = ""
        else:
            data, payload = payload[:length], payload[length:]
            self.logger.debug("payload: %r, length: %d", payload, len(payload))
            value = struct.unpack('%ds' % length, data)
            value = value[0].strip('\x00')
            if self.reverse:
                value = "".join(reversed(value))
            dikt[self.name] = value
        return payload, dikt

    def encode_len(self, length, dikt):
        if length == -1: # consumer case
            data = dikt[self.name]
            return len(data), dikt
        else:
            return length, dikt

    def decode_len(self, length, payload):
        if length == -1: # consumer case
            return len(payload), ""
        else:
            return length, payload[length:]

    def __getitem__(self, key):
        """
        This method provides a convenient shorthand notation for specifying
        :py:class:`.String` token and directly wrapping it in an appropriate
        :py:class:`.LengthSpecifier`. You  This:

        >>> from striptease import Consumer, String, uint_8
        >>> struct = Struct().append(
        ...     uint_8('strlen')
        ...     Dynamic('strlen', String('bar')),
        ...     Static(10, String('moo')),
        ...     Consumer(String('foo')),
        ... )

        is equivalent to this:

        >>> from striptease import Consumer, String, uint_8
        >>> struct = Struct().append(
        ...     uint_8('strlen'),
        ...     String('bar')['strlen'],
        ...     String('moo')[10],
        ...     String('foo')[None],
        ... )
        """
        if not key:
            return Consumer(self)
        else:
            if type(key) == int:
                return Static(key, self)
            elif type(key) == str:
                return Dynamid(key, self)
            else:
                pass # TODO: raise Error


def construct_array(token, len):
    """
    Convenience function to create an array from a given token-instance.
    Can construct dynamic, static and comsumer type arrays with the given
    token's type.

    TODO: examples.
    """
    reverse = getattr(token, 'reverse', False)
    if not len:
        return Consumer(Array(token.name, reverse).of(token))
    else:
        if type(len) == int:
            return Static(len, Array(token.name, reverse).of(token))
        elif type(len) == str:
            return Dynamic(len, Array(token.name, reverse).of(token))
        else:
            pass # TODO: raise Error


def array_factory(cls):
    """
    A class decorator for adding a shorthand notation for specifiying arrays
    of the decorated class-token.

    .. warning::
        This decorator replaces the cls.__getitem__ method, so must have it
        still free.
    """
    cls.__getitem__ = construct_array
    return cls

