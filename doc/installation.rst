Installation
============

Dependencies
------------

This alpha-release has been tested with Python 2.6 and 2.7 solely. If you have
issues using striptease with any other version of the Python 2.x series, drop
me a bug report.

In addition :py:mod:`crcmod` is needed for computing and verifying
checksums.

Striptease has two optional dependencies:

* Install :py:mod:`bitstring` for bitstring support
* Install :py:mod:`logbook` for improved logging support

Installation procedure
----------------------

Striptease can be installed using :py:mod:`distutils`. Run the following
command::

  python setup.py install


Unit Testing
------------
You can unit-test striptease before the install via `nose`. You can find all
the tests within the `test` directory.

