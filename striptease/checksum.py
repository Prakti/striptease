# -*- coding: utf-8 -*-
"""
    striptease.checksum
    ~~~~~~~~~~~~~~~~~~~

    This module provides several checksum-token for use in stripteases
    encoder/decoder trees.

    :copyright: Copyright 2011 by the University of Paderborn
    :license: BSD, see LICENSE for details
"""

from crcmod import Crc
from crcmod.predefined import PredefinedCrc

from striptease.base import Integer
from striptease.util import logged


@logged()
class Checksum(Integer):
    """
    This is the abstract base class, providing some convenience code for all
    sub-classes. Checksums need to behave differently from other token:

    On encoding, a ``Checksum`` lets its child encode the binary data to be
    checksummed, then calculates its checksum and appends it. On decoding,
    it's vice versa: first the checksum is stripped from the back of the
    binary data, then the binary data is checked and then handed for decoding
    to the child.

    You can create your own checksum token by subclassing ``Checksum`` and
    overriding the ``checksum(self, bytes)`` method. ``bytes`` is excpected to
    be of type ``str``.
    """

    def __init__(self, name, length, endian='!'):
        self.child = None
        Integer.__init__(self, name, False, length, endian)

    def child(self, child):
        self.child = child
        return self

    def encode(self, dikt, payload):
        _payload = self.child.encode(dikt, '')
        chksum = self.checksum(_payload)
        dikt[self.name] = chksum
        dikt, _payload = Integer.encode(self, dikt, _payload)
        return dikt, payload + _payload

    def decode(self, payload, dikt):
        """
        1.) Determine length of child and slice off respective payload
        2.) Slice off checksum bytes
        3.) Calculate checksum from child payload
        4.) decode child
        5.) Return remaining payload

        If the checksum is not correct an exception is raised
        """
        self.logger.info("data payload %r" % payload)

        child_len = self.child.length(payload)
        if child_len == len(payload): # consumer case
            child_len -= self.length  # reduce child-length by checksum
        child_payload = payload[:child_len]
        chk_bytes = payload[child_len:self.length]
        _payload = payload[child_len + self.length:] # remaining payload

        chk_bytes, dikt = Integer.decode(self, chk_bytes, dikt)
        chk_sum = self.checksum(self, child_payload)

        if dikt[self.name] != chk_sum:
            raise ValueError('Checksum failure for %s'  % self.child.name)
        else:
            child_payload, dikt = self.child.decode(child_payload, dikt)
            return _payload, dikt

    def checksum(self, bytes):
        raise AttributeError("Implement this")


class XOR(Checksum):
    """
    A simple XOR over chunks of `length` bytes. Just some sort of parity
    checksum.
    """

    def __init__(self, name, length, endian='!'):
        self.bitmask = int('1' * 8 * length, 2)
        Checksum.__init__(self, name, length, endian)

    def checksum(self, bytes):
        chk_sum = self.bitmask
        while bytes:
            chunk, bytes = bytes[0:self.length], bytes[self.length:]
            chk_sum ^= sum(ord(c) for c in chunk)
        return chk_sum


class CRC(Checksum):
    """
    Uses the `crcmod.Crc` class for calculating proper CRC's. Expects a
    generator polynom `poly` either as an `int` or as a `str`. If `poly` is a
    `str` it is interpreted as a name of a well-known crc-function and looked
    up from `crcmod.predefined` using the `crcmod.predefined.PredefinedCRC`
    module.
    """

    def __init__(self, name, poly, endian='!'):
        if type(poly) == str:
            self.crc = PredefinedCrc(poly)
        elif type(poly) == int:
            self.poly = poly
            self.crc = Crc(poly)
        Checksum.__init__(self, name, self.crc.digest_size, endian)

    def checksum(self, bytes):
        crc = self.crc.new(bytes)
        return int(crc.hexdigest(), 16)

