API Documentation
=================

The Central idea of striptease is to build a :py:class:`structure <.Struct>`
of :py:class:`.Token` and then to traverse it for encoding and decoding. You
can think of it like manually creating an abstract syntax tree of a domain
specific language. Since I did not want to overly mess around with internal
Python features, the description syntax of striptease tries to balance a clean
implementation with a compact readable syntax.


Token and Structure
-------------------

.. autoclass:: striptease.base.Token
   :members: encode, decode, length, encode_len, decode_len

.. autoclass:: striptease.base.Struct
   :members: append

.. autoclass:: striptease.base.Padding


Numbers
-------

For numerical values :py:class:`.Number` serves as a base class, bundling
common code for :py:class:`.Float` and :py:class:`.Integer`. For convenience,
striptease offers several predefined constructors for various numerical
encoders and their different bitlength. 

.. autoclass:: striptease.numbers.Number
   :members: fmt

.. autoclass:: striptease.numbers.Integer

.. autoclass:: striptease.numbers.Float


Predefined Factories for C99-lookalike Number Token:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Striptease offers Factories for creating Number-Token with a C99 lookalike
syntax.  Thus, for creating a token for a 8-Bit signed integer you can write:

.. doctest:: api

   >>> from striptease import uint8
   >>> token = uint8('foo')

Which is equivalent to:

.. doctest:: api

   >>> from striptease.numbers import Integer
   >>> token = Integer('foo', True, 1)

Striptease provides factories for ``uint8`` to ``uint64`` and from ``ìnt8`` to
``int64`` respectively. In addition it provides factories for ``single`` (4
byte floats) and ``double`` (8 byte floats).

In addition these factories provide a more C-like syntax when specifying
arrays of a numeric type. So you could specify a token for an array of
uinsigned 32-Bit integers with a length of 10 elements like this:

.. doctest:: api

   >>> from striptease import uint32
   >>> array_token = uint32('bar')[10]

Which is equivalend to:

.. doctest:: api

   >>> from striptease.sequences import Static
   >>> array_token = Static(10, uint32('bar'))

Or even longer:

.. doctest:: api

   >>> array_token = Static(10, Integer('foo', True, 4))


Sequences and Length
--------------------

In order to realize flexible :py:class:`.Token` for sequences like arrays and
strings, I first defined several :py:class:`.LengthSpecifier` token,
:py:class:`.Dynamic` where the length of the sequence is specified in the
bytestream, :py:class:`.Static` for predefined length within the data
structure and :py:class:`.Consumer` for blob-like objects.  These
:py:class:`.LengthSpecifier` then embed a :py:class:`.Sequence` token:
:py:class:`.Array` or :py:class:`.String`.

.. autoclass:: striptease.sequences.Sequence
   :members: encode, decode, length, encode_len, decode_len

.. autoclass:: striptease.sequences.Array
   :members: of, decode, consume, extract, atype_length

.. autoclass:: striptease.sequences.String
   :members: __getitem__


LengthSpecifiers for use with Sequences
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: striptease.sequences.LengthSpecifier

.. autoclass:: striptease.sequences.Dynamic

.. autoclass:: striptease.sequences.Static

.. autoclass:: striptease.sequences.Consumer


Convenience Functions
---------------------

.. autofunction:: striptease.sequences.construct_array

.. autofunction:: striptease.sequences.array_factory


