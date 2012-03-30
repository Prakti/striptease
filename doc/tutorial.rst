Striptease Tutorial
===================

I one of my research projects, I once had to write my own decoding library
from supplied documentation. Since I was talking to a microcontroller, I was
dealing with a very compact binary format which was basically constructed from
simple C structs.

Since I needed to tinker with the peculiarities of the protocol, I decided to
do my first experiments with Python's :py:mod:`struct` library. But soon I
stumbled over encoded arrays of either a fixed or dynamic length and working
with :py:mod:`struct` became tedious. I wanted a readable and reusable
solution. My Idea was to specify the structure of the packets in a tree and
traverse this tree for decoding and encoding the packets. 


A simple example
----------------
Let's say we just want to encode a simple 64 Bit integer.
.. doctest:: tutorial

  >>> from striptease import uint64
  >>> token = uint64('foo')
  >>> values = dict(foo=4493203949)
  >>> values_, payload = token.encode(values, '')
  >>> values_ == values
  True
  >>> payload
  '\x00\x00\x00\x0b\x80\r\xad\x90'

As you can see, it's quite straightforward. We give the token a name and for
encoding we hand a dictionary to ``token.encode`` and an empty bytestring and
out come the same dictionary and the payload with the appended encoded data.
Decoding now works directly the other way round:
.. doctest:: tutorial

   >>> rest, decoded = token.decode(payload, dict())
   >>> rest == ''
   True
   >>> decoded == values
   True
   >>> decoded
   {'foo': 49393020304}

The payload is consumed into an empty string and the supplied dict is filled
with the correct decoded values.

Numbers
-------
Beneath ``uint64`` you can import a lot of other C99 lookalike token from
striptease: ``uint8`` to ``uint64``, signed ``int8`` to ``int64`` and floats
of 32 Bit and 64 Bit length: ``single`` and ``double``.


Structures
----------
You can directly imitate C structures with striptease and use the resulting
object for decoding and encoding. That's why we have to hand over a dictionary
to ``encode`` and ``decode`` so both methods can look up the named token in
the struct up for storing and retrieving values. But let's have another
example to clarify this. This is the C struct you want to imitate:

.. code-block:: c
  
   struct message {
       uint8_t foo;
       int32_t baz;
       int16_t bar;
       uint8_t bang;
   };

You can directly imitate it like this:
.. doctest:: tutorial

   >>> from striptease import uint8, int16, int32, Struct
   >>> 
   >>> message = Struct().append(
   ...     uint8('foo'),
   ...     int32('baz'),
   ...     int16('bar'),
   ...     uint8('bang')
   ... )

And then you can use it for encoding and decoding:
.. doctest:: tutorial

   >>> values = {
   ...   'bang': 120,
   ...   'foo' : 16,
   ...   'bar' : -400,
   ...   'baz' : 80000,
   ... }
   >>> values_, payload = message.encode(values, '')
   >>> payload
   '\x10\x00\x018\x80\xfepx'
   >>> values_ == values
   True
   >>> message.decode(payload, dict())
   ('', {'bar': -400, 'bang': 120, 'foo': 16, 'baz': 80000})
   >>> 


Arrays of Fixed Length
----------------------
To each number-token, you can directly create sequence token, similar how you
would specify arrays in C:
.. doctest:: tutorial

   >>> token = uint8('foo')[10]

This resembles an uint8_t array of size 10. The values to be encoded must be
sequences with the appropriate length:
.. doctest:: tutorial

   >>> values = { 'foo' : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] }
   >>> values_, payload = token.encode(values, '')
   >>> payload
   '\x01\x02\x03\x04\x05\x06\x07\x08\t\n'

Again decoding produces the expected Python datastructures:
.. doctest:: tutorial

   >>> rest, decoded = token.decode(payload, dict())
   >>> decoded == values
   True
   >>> decoded
   {'foo': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}


Arrays of Dynamic Lenght
------------------------
The real awesomeness is how striptease enables us to specify arrays of dynamic
lenght, but this only works inside of a ``Struct``.  Let's say the following C
snippet describes the structure of a packet, sent over a serial line or UDP,
with the ``len`` field specifying the actual length of the ``data`` array.

.. code-block:: c

   struct message {
       uint8_t   id;
       uint8_t   len;
       uint8_t   data[MAX_LEN];
   };

With striptease, you can recreate this structure, and use it to encode and
decode data. That's how the structure is recreated with striptease:

.. doctest:: tutorial

   >>> from striptease import uint8, int16, int32, Struct
   >>>
   >>> message = Struct().append(
   ...     uint8('id'),
   ...     uint8('len'),
   ...     uint8('data')['len'],
   ... )

For encoding, need not provide data for the ``len`` field, because striptease
will automaticall figure it out. Since ``len`` is explicitly specified in the
definition of the array-token, it has to occur anywhere *before* it in the
``Struct``.

.. doctest:: tutorial

   >>> values = dict(id=2, data=[1,2,3,4,5,6,7,8])
   >>> values_, payload = message.encode(values, '')
   >>> payload
   '\x02\x08\x01\x02\x03\x04\x05\x06\x07\x08'

On the other hand, this mechanism also helps upon decoding a binary payload:
The data is decoded iteratively from the payload, thus the len of an array is
already determined and stored in a ``dict`` and can be used for decoding the
array. Since the array-token knows which token represents its length it can
retrieve that value from the ``dict``. Nice and easy.

