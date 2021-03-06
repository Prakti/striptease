.. Striptease documentation master file, created by
   sphinx-quickstart on Thu Jan 20 09:46:34 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Striptease 
=====================

Striptease is used for encoding and decoding binary data, but the sexy way!
It is designed to handle binary data in cases where ASN.1 or Google-Protobuf
would be overkill, but the standard :py:mod:`struct` library would be too unwieldy.

Let's say the following C snippet describes the structure of a packet, sent
via UDP, with the ``len`` field specifying the actual length of the ``data``
array.

.. code-block:: c

   struct message {
       uint8_t   id;
       uint8_t   len;
       uint8_t   data[MAX_LEN];
   };

With striptease, you can recreate this structure, and use it to encode and
decode data.

.. doctest:: index

   >>> from striptease import Struct, uint8
   >>> message = Struct().append(
   ...     uint8('id'),
   ...     uint8('len'),
   ...     uint8('data')['len'],
   ... )
   >>> values = {
   ...     'id' : 100,
   ...     'data' : range(20),
   ... }
   >>> values
   {'data': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19], 'id': 100}
   >>> values, bytes = message.encode(values)
   >>> bytes
   'd\x14\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13'
   >>> bytes = '@\x10\x0f\x0e\r\x0c\x0b\n\t\x08\x07\x06\x05\x04\x03\x02\x01\x00'
   >>> bytes, values = message.decode(bytes, dict())
   >>> values
   {'data': [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0], 'id': 64, 'len': 16}

As we can see from the above example, the value for the ``len`` field is
automatically determined during the encoding phase, by examining the value of
the ``data`` field. Of course you can also specify arrays of a fixed size:

.. doctest:: index

   >>> array = uint8('foo')[10]
   >>> array.encode({'foo' : range(10)})
   ({'foo': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}, '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t')   
   >>> bytes = '\x13\x12\x11\x10\x0f\x0e\r\x0c\x0b\n'
   >>> array.decode(bytes, dict())
   ('', {'foo': [19, 18, 17, 16, 15, 14, 13, 12, 11, 10]})


Contents:
=========

.. toctree::
   :maxdepth: 2

   installation
   tutorial
   api
   example


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

