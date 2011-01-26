# -*- coding: utf-8 -*-

try:
    from bitstring import BitString
    from striptease import Bitfield

    def test_bitfield():
        pack = Struct().append(
            Bitfield('foo', 128),
            Bitfield('bar', 10)
        )
        hex = '0x' + ('00' * 128)
        dikt = {
            'foo' : BitString(hex),
            'bar' : (0, 1, 0, 0, 1, 1, 1, 0)
        }
        dikt['foo'][1] = 1
        dikt['foo'][64] = 1
        payload = ""
        payload = ""
        print "payload: %r, dikt: %s" % (payload, dikt)
        dikt, payload = pack.encode(dikt, payload)
        print "payload: %r, dikt: %s" % (payload, dikt)
        dikt = dict()
        print "payload: %r, dikt: %s" % (payload, dikt)
        payload, dikt = pack.decode(payload, dikt)
        print "payload: %r, dikt: %s" % (payload, dikt)
except ImportError:
    print "Could not find 'bitstring' library. Cannot test Bitfield Token"
