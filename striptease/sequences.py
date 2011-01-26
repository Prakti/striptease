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

    `Static`:
            The size of the array or string is fixed

    `Dynamic`:
            The size of the array or string is determined by an integer number
            preceding the array or string

    `Consumer`:
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
    Used to specify ``Sequences`` of a fixed type.

    :param length: must be an integer value, determines the lenght in *pointer
                   increments*, similar to C arrays, not in bytes.
    :param seqtype: instance of a subclass of ``Sequence``.
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
    Used to specify ``Sequences`` which have a preceding length-field. This
    length-field must precede the sequence data in the bytestream but does not
    have to do so diretly, i.e. other data may be in between the length-field
    and the actual sequence.

    :param len_name: is the name of the token specifying the length of the
                     sequence
    :param seqtype:  is the instance of a subclass of ``Seqcuence``
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
        When a ``Struct`` registers itself as a parent, we look up the token
        encoding our length and mokey-patch it's ``encode`` method. That way,
        the length of the dynamic array can be determined on the fly during
        encoding.

        Analogous, the lenght-token's ``decode_len`` method is patched, since
        this class' ``decode_len`` method needs the length information from
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
    This ``LengthSpecifier`` is used for blob-like objects, when you want to
    encode sequences of arbitrary size, without specifying an actual length.
    When decoding, the ``Consumer`` tells its ``Sequence`` to try and decode
    all remaining binary data. Because of that, ``Consumer`` sequences must be
    the last token in a struct. They may not work in combination with nested
    ``Structs``. You have been warned.
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
    Abstract base class for all sequence token.
    """

    def __init__(self):
        Token.__init__(self)

    def encode_len(self, lenght, dikt):
        AttributeError("Not implemented")

    def decode_len(self, length, payload):
        AttributeError("Not implemented")

    def length(self, length, parm):
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
    initialization, you must specify the type of the array via the ``of``
    method, which returns ``self``, so you can chain instantiation and
    array-type specification in one go.
    """

    def __init__(self, name, reverse=False):
        Token.__init__(self)
        self.name = name
        self.reverse = reverse
        self.atype = None

    def of(self, atype):
        self.atype = atype
        self.atype.parent = self
        return self

    def encode(self, length, dikt, payload=""):
        """
        Extract data by name from dikt, encode and append to payload
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
        Try and decode all of the remaining payload.
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
        Slice length * self.atype.length bytes from front of payload,
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
        Based on the length, this method dispatches to two other methods (for
        readability reasons):

        ``consume``:
                in case the wrapping length-specifier is a ``Consumer`` and
                hands over a length of -1

        ``extract``:
                in case the wrapping length-specifier can supply an actual
                length.
        """
        if length == -1:
            return self.consume(payload, dikt)
        else:
            return self.extract(length, payload, dikt)

    def atype_length(self, parm):
        """ Convenience wrapper for accessing the length of the array-type """
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
class String(Token):
    """ Class for encoding bytestrings into a payload """

    def __init__(self, name, endian='!', reverse=False):
        Token.__init__(self)
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

    ..warning::
        This decorator replaces the cls.__getitem__ method, so must have it
        still free.
    """
    cls.__getitem__ = construct_array
    return cls

