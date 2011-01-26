# -*- coding: utf-8 -*-

import string
import random

from striptease import Padding, Struct, Integer,\
                       uint_8, uint_16, uint_32, single

#TODO: more tests to check corner cases and improve code-coverage

def test_struct():
    coder_token = Struct().append(
        uint_8('foo'),
        Padding('asdf'),
        uint_16('bar'),
        Struct('baz').append(
            uint_32('moo'),
            single('meh')
        )
    )

    for i in range(100):
        foo = random.getrandbits(8)
        bar = random.getrandbits(16)
        moo = random.getrandbits(32)
        meh = random.getrandbits(8)
        meh = float.fromhex(hex(meh).strip('L'))

        in_dikt = {
            'foo' : foo,
            'bar' : bar,
            'baz' : {
                'moo' : moo,
                'meh' : meh,
            }
        }

        tmp_dikt, payload = coder_token.encode(in_dikt)
        assert payload
        assert payload[1:5] == 'asdf', "%s != %s" % (payload[1:6], 'asdf')
        assert tmp_dikt == in_dikt

        payload, out_dikt = coder_token.decode(payload, dict())
        assert out_dikt == in_dikt, "\n%s != \n%s" % (out_dikt, in_dikt)
        assert out_dikt['bar'] == bar, "%d != %d" % (out_dikt['bar'], bar)
        assert payload == ''

