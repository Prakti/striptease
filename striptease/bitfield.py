# -*- coding: utf-8 -*-
"""
    striptease.bitfield
    ~~~~~~~~~~~~~~~~~~~

    Bitfield encoding support for striptease.

    ..warning:: has the bitstring library as dependency
"""

from bitstring import BitString


class Bitfield(Token):

    def __init__(self, name, bytecount):
        Token.__init__(self)
        self.name = name
        self.bytecount = bytecount

    def encode(self, dikt, payload):
        """
        The value to be encoded must be a ``BitString``, or alternatively may
        be a sequence of objects which result to boolean ``False`` or
        ``True``.
        """
        value = dikt[self.name]
        if type(value) == BitString:
            payload += value.bytes
        else:
            value = [('1' if b else '0') for b in value]
            payload += BitString('0b' + "".join(value)).bytes
        return dikt, payload

    def decode(self, payload, dikt):
        data, payload = payload[:self.bytecount], payload[self.bytecount:]
        value = BitString(bytes=data)
        dikt[self.name] = value
        return payload, dikt
