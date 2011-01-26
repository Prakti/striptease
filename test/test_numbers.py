# -*- coding: utf-8 -*-

import random

from striptease import Integer, Float

#TODO: more tests to check corner cases and improve code-coverage

def test_integers():
    for sign in [True, False]:
        for length in [1,2,4,8]:
            for endian in ['>', '<', '@', '!', '=']:
                coder_token = Integer('foo', sign, length, endian)
                for j in range(100):
                    value = random.getrandbits((length * 8) - 1)
                    if sign:
                        value *= (-1 if random.choice([True, False]) else 1)
                    dikt, payload = coder_token.encode({
                        'foo' : value
                    })
                    assert value == dikt['foo']
                    assert payload
                    payload, dikt = coder_token.decode(payload, dict())
                    assert value == dikt['foo']
                    assert payload == ''


def test_floats():
    for length in [4,8]:
        for endian in ['>', '<', '@', '!', '=']:
            coder_token = Float('foo', length, endian)
            for j in range(100):
                value = random.getrandbits(length)
                value = float.fromhex(hex(value).strip('L'))
                value += (-1 if random.choice([True, False]) else 1)
                dikt, payload = coder_token.encode({
                    'foo' : value
                })
                assert value == dikt['foo'], "%f, %f" % (value, dikt['foo'])
                assert payload
                payload, dikt = coder_token.decode(payload, dict())
                assert value == dikt['foo'], "%f, %s" % (value -
                        dikt['foo'], coder_token.length)
                assert payload == ''
