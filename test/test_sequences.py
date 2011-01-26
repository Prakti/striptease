# -*- coding: utf-8 -*-

import string
import random

from striptease import Struct, Dynamic, Static, Consumer, Array,\
                       String, Integer, uint_8


#TODO: more tests to check out all corner cases


def test_static_int_array():
    for length in [1,2,4,8]:
        for endian in ['<', '>', '@', '=', '!']:
            for reverse in [True, False]:
                for sign in [True, False]:
                    coder_token = Static(10,
                                    Array('foo', reverse).of(
                                        Integer('', sign, length)))
                    data = [random.getrandbits((8 * length) - 1) for i in range(10)]
                    if sign:
                        signed = [True, False]
                        data = [i * (-1 if random.choice(signed) else 1) for i in data]
                    in_dikt = {'foo' : data}
                    temp_dikt, payload = coder_token.encode(in_dikt)
                    assert temp_dikt == in_dikt
                    assert payload
                    payload, out_dikt = coder_token.decode(payload, temp_dikt)
                    assert out_dikt == in_dikt
                    assert payload == ''


def test_dynamic_int_array():
    for length in [1,2,4,8]:
        for endian in ['<', '>', '@', '=', '!']:
            for reverse in [True, False]:
                for sign in [True, False]:
                    for lenlen in [1,2,4,8]:
                        coder_token = Struct().append(
                            Integer('foo_len', False, lenlen, endian),
                            Dynamic('foo_len', Array('foo', reverse).of(
                                                     Integer('', sign, length)))
                        )
                        foo_len = random.randrange(10, 255, 8)
                        data = [random.getrandbits((8 * length) - 1)
                                for i in range(foo_len)]
                        if sign:
                            signed = [True, False]
                            data = [i * (-1 if random.choice(signed) else 1) for i in data]
                        in_dikt = {'foo_len' : lenlen, 'foo' : data}
                        temp_dikt, payload = coder_token.encode(in_dikt)
                        assert temp_dikt == in_dikt
                        assert payload
                        payload, out_dikt = coder_token.decode(payload, temp_dikt)
                        assert out_dikt == in_dikt
                        assert payload == ''


def test_string():
    for endian in ['<', '>', '@', '=', '!']:
        for reverse in [True, False]:
            for i in range(100):
                print "endian = %s, reverse = %s, i = %d" % (endian, reverse, i)
                slen = random.getrandbits(8)
                coder_token = Struct().append(
                    uint_8('foo_len'),
                    Dynamic('foo_len', String('foo', endian, reverse)),
                    Static(slen, String('bar', endian, reverse)),
                    Consumer(String('moo', endian, reverse))
                )
                foo_len = random.getrandbits(7) + 10
                bar_len = random.getrandbits(7) + 10
                moo_len = random.getrandbits(7) + 10
                foo = "".join(random.sample(string.printable * foo_len, foo_len))
                bar = "".join(random.sample(string.printable * bar_len, bar_len))
                moo = "".join(random.sample(string.printable * moo_len, moo_len))
                in_dikt = { 'foo' : foo, 'bar' : bar, 'moo' : moo }
                tmp_dikt, payload = coder_token.encode(in_dikt)
                in_dikt['bar'] = bar[:slen]
                tmp_dikt['bar'] = bar[:slen]
                assert in_dikt == tmp_dikt
                payload, out_dikt = coder_token.decode(payload, dict())
                assert in_dikt == out_dikt, "\n%s == \n%s" % (in_dikt, out_dikt)
                assert payload == ""


