Striptease Tutorial
===================

In this tutorial I will introduce a small example on how to create a custom
message stack which uses striptease to make encoding, decoding specific
messages very easy. This is also one of the few examples where metaclasses in
python actually make sense. I've searched for other elegant ways to create
such a message stack but even after trying out other ideas, this looked like
the best.

Our goal is a class structure where we can encode and decode instances of a
message class by simply typing::

    bytestream = msg.encode()
    msg = Message.decode(bytestream)

where ``Message`` is the abstract base class of all messages of the protocol
and ``msg`` is an instance of a subclass of ``Message``. The interesting part
is going to happen in ``Message.decode`` because the function should examine
the header of the message and deduce what type of message this is, then decode
the payload data into the corresponding subclass of ``Message``.


Creating an Autodecoding Message Stack
--------------------------------------

Therefore, we create a mechanism which automatically registers subclasses of
``Messages`` into some sort of registry, where ``Message.decode`` can find the
class, based on some ID. This is done via the ``Decoder`` metaclass::

    class Decoder(type):

        REGISTRY = dict()

        def __new__(mcs, name, bases, dikt):
            cls = type.__new__(mcs, name, bases, dikt)
            msgid = dikt['MSG_ID']
            if msgid in mcs.REGISTRY:
                raise LookupError('MsgID: 0x%X already assigned to %s' %
                        (msgid, mcs.REGISTRY[msgid]))
            dikt['REGISTRY'] = mcs.REGISTRY
            mcs.REGISTRY[msgid] = cls
            return cls


A metaclass overrides the standard functionality with which classes are
created. Normally ``type`` is invoked with the following parameters: 
``name`` is the name of the new class, ``bases`` is a list containing the
baseclasses of the class and ``dikt`` is a dictionary containing all the
class-attributes of the new class. Basically ``dikt`` is represents the
namespace of the class before instantiation. 

Now we use the metaclass to register the class object created by::

  cls = type.__new__(mcs, name, bases, dikt)

with the registry. To do so we rely on some implicit convention, namely that
each class has a class-attribute called ``MSG_ID`` under which it can be
registered. 

Afterwards we  inject this ``REGISTRY`` into the newly created class to make
it available there, so it can be used by the Abstract Base Class for the
``decode`` function. Now we can create that Abstract Base Class::

  class Message(object):
      """
      Base class for all messages, uses the Decoder metaclass to automatically
      provide a decoding-service to all its subclasses. Subclasses *must*
      provide a MSG_ID > 0 and a STRUCTURE which must be at least a subclass
      of striptease.Token.
      """

      __metaclass__ = Decoder

      MSG_ID = -1
      HEADER = Struct().append(
          uint8('msg_id'),
          uint16('length'),
      )

      LENGTH_ERR = "Packet lenght is {0}, {1} expected!"

      def update(self, dikt):
          self.__dict__.update(dikt)

      @classmethod
      def decode(cls, data):
          # Decode Header and determine msg-type
          payload, dikt = cls.HEADER.decode(data, dict())
          msg = cls.REGISTRY[dikt['msg_id']]()
          assert len(payload) == (dikt['length']),\
                  LENGTH_ERR.format(len(payload), dikt['length'])
          # Decode payload and update the internal data
          msg.STRUCTURE.decode(payload, dikt)
          msg.update(dikt)
          return msg

      def encode(self):
          dikt, payload = self.STRUCTURE.encode(self.__dict__)
          header_data = dict(msg_id = self.MSG_ID, length = len(payload))
          dikt, header = self.HEADER.encode(header_data)
          return header + payload

      def process(self, handler):
          msg = "Subclass must implement this, but {0} doesn't"
          raise NotImplementedError(msg.format(type(self)))

In order to fulfill the convention ``Message`` also provides a ``MSG_ID`` but
assuming the ``MSG_ID`` is an unsigned int, it uses an invalid negative number
to indicate that it isn't meant to be instantiated. Also ``Message`` uses
``striptease`` for a compact and easy-to-use specification of the header-data 
from which the type of ``Message`` is deduced.

This ``HEADER`` comes actively into play in the ``decode`` and ``encode``
methods. As can be seen ``decode`` takes the bytestream ``data``, then decodes
the ``HEADER`` into a ``dict`` and then looks up the proper subclass from 
``cls.REGISTRY``. Now the second convention for all subclasses of ``Message``
come into play. Beneath ``MSG_ID``, each must provide the ``STRUCTURE`` of
it's payload data, described by a ``striptease.Struct``, as a class attribute.
The third convention is, that all subclasses of ``Message`` have default
values in their constructors, so ``decode`` can instantiate them without
knowing the proper parameters. The decoded values are ``updated`` into the
instance.

In comparison ``encode`` is a bit more straightforward, it starts with an
instance of a subclass of ``Message``, uses ``msg.STRUCTURE`` to create the
binary data for the payload and then encodes and prepends the ``HEADER``.


Creating a Storage Service
--------------------------
The idea: have a service that can store Python objects from a remote system.
We will use the ``marshal`` module to create string representations of Python
objects and send them ``base64`` encoded over the wire to a remote server,
which simply stores them as strings in a GNU DBM (basically a persistent
dictionary). The communication part will be done by the ``asyncore`` module.

The whole thing is more ore less message-driven so lets start with examining
the messages. In order to easily map messages to the appropriate actions, each
message will implement a ``process`` method which will encapsulate the actions
associated with a receiving of such a message.

Store Transaction
~~~~~~~~~~~~~~~~~~~
Only two messages are needed. A ``StoreRequest`` containing the data and the
name to be stored, together with a transaction-number for tracking multiple
parallel transactions::

  class StoreRequest(Message):

      MSG_ID = 0x01
      STRUCTURE = Struct().append(
          uint8('trans'),
          uint8('nlen'),
          String('name')['nlen'],
          uint16('dlen'),
          String('data')['dlen'],
      )

      def __init__(self, trans=0, name='', data=''):
          self.trans = trans
          assert len(name) < 0xFF
          self.name = name
          assert len(data) < 0xFFFF
          self.data = data

      def process(self, handler):
          status = handler.store(self.name, self.data)
          return StoreResponse(self.trans, self.name, status)

      @classmethod
      def marshal(cls, trans, name, data):
          data = b64encode(marshal.dumps(data))
          return cls(trans, name, data)

      def unmarshal(self):
          return self.name, marshal.loads(b64decode(self.data))

On the server-side a ``handler`` answers this ``StoreRequest`` by a
``StoreResponse`` containing the transaction-number, the name of the stored
object and a status code indicating success or type of failure::

  class StoreResponse(Message):
      """
      Sent as a reply upon a StoreRequest, indicating the status of the
      operation.
      """

      MSG_ID = 0x02
      STRUCTURE = Struct().append(
          uint8('trans'),
          uint8('nlen'),
          String('name')['nlen'],
          uint8('status'),
      )

      def __init__(self, trans=0, name='', status=-1):
          self.trans = trans
          assert len(name) < 0xFF
          self.name = name
          self.status = status

      def process(self, client):
          client.store_done(self)

Note how the use of ``striptease`` keeps the code clean and accessible.
The whole task of hooking the subclasses into the registry is elegantly done
by the metaclass, while ``STRUCTURE`` reveals the data-layout for debugging
without bothering the programmer with the gory details of decoding and
encoding. 


Fetch Transaction
~~~~~~~~~~~~~~~~~
Again we need two messages for fetching data from the server, a
``FetchRequest`` and a ``FetchResponse``::

  class FetchRequest(Message):

      MSG_ID = 0x03
      STRUCTURE = Struct().append(
          uint8('trans'),
          uint8('nlen'),
          String('name')['nlen'],
      )

      def __init__(self, trans=0, name=''):
          self.trans = trans
          assert len(name) < 0xFF
          self.name = name

      def process(self, handler):
          status, data = handler.fetch(self.name)
          return FetchResponse(self.trans, status, self.name, data)


  class FetchResponse(Message):

      MSG_ID = 0x04
      STRUCTURE = Struct().append(
          uint8('trans'),
          uint8('status'),
          uint8('nlen'),
          String('name')['nlen'],
          uint16('dlen'),
          String('data')['dlen']
      )

      def __init__(self, trans=0, status=-1, name='', data=None):
          self.trans = trans
          self.status = status
          self.name = name
          self.data = data

      def process(self, client):
          client.fetch_done(self)

      def unmarshal(self):
          return self.name, marshal.loads(b64decode(self.data))


Processing the Messages:
~~~~~~~~~~~~~~~~~~~~~~~~
For communicating over the network I have chosen to use the available
``asyncore`` module. Specifically we need three entities: a ``StorageServer``
which spawns a ``StorageHandler`` for each incoming connection and a
``StorageClient`` communicating with the ``StorageHandler``.
Let's start with the ``StorageServer`` since it is that simple::

  class StorageServer(asyncore.dispatcher):

      def __init__(self, host, port):
          asyncore.dispatcher.__init__(self)
          self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
          self.set_reuse_addr()
          self.bind((host, port))
          self.listen(5)

      def handle_accept(self):
          pair = self.accept()
          if pair is None:
              pass
          else:
              sock, addr = pair
              print('Incoming connection from %s' % repr(addr))
              handler = StorageHandler(sock, addr)
              
The ``StorageHandler`` is of course more complex, it has to open the GNU DBM
for storing the data for the client and it has to handle the incoming
messages::

  class StorageHandler(asyncore.dispatcher_with_send):

      SUCCESS = 0x00
      EIO = 0x01
      EKEY = 0x02
      FAIL = 0xFF

      def __init__(self, sock, addr):
          asyncore.dispatcher_with_send.__init__(self, sock)
          self.addr = addr
          self.db = gnudbm.open(str(addr) + '.dbm', 'c')

      def handle_read(self):
          data = self.recv(4096)
          if data:
              msg = Message.decode(data)
              reply = msg.process(self)
              if reply:
                  self.send(reply.encode())

      def handle_close(self):
          print("Closing database for {0}".format(self.addr))
          self.db.close()
          self.close()

      def store(self, name, data):
          status = self.FAIL
          try:
              self.db[name] = data
              status = self.SUCCESS
          except gnudbm.error as e:
              print(e)
              status = self.EIO
          except KeyError as e:
              print(e)
              status = self.EKEY
          finally:
              return status

      def fetch(self, name):
          data = ''
          status = self.SUCCESS
          try:
              data = self.db[name]
          except gnudbm.error as e:
              status = self.EIO
          except KeyError as e:
              status = self.EKEY
          finally:
              return status, data

As you can see, the ``handle_read`` method for receiving the binary data
from the network is rather compact, as it uses the messages' ``process``
method to dispatch into either ``store`` or ``fetch`` and to create the
appropriate reply. In addition ``store`` and ``fetch`` just provide some 
convenience functionality; everything that has to be done upon the reception
of a ``StoreRequest`` or a ``FetchRequest`` is bundled with it's appropriate
message, which is quite sensible in my opinion.

The ``StorageClient`` is a bit more complex in code, but the larger part of
it revolves around tracking the transaction corresponding to the received
message and dispatching the results of transactions into callbacks::

  class StorageClient(asyncore.dispatcher_with_send):

      TRANS = 0

      def __init__(self, host, port):
          asyncore.dispatcher_with_send.__init__(self)
          self.lock = threading.RLock()
          self._connected = False
          self.callbacks = dict()
          self.error_callbacks = dict()
          self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
          self.connect((host, port))

      @property
      def connected(self):
          with self.lock:
              self._connected = True

      @connected.setter
      def connected(self, state):
          with self.lock:
              self._connected = state

      def handle_connect(self):
          self.connected = True

      def handle_read(self):
          data = self.recv(4096)
          if data:
              msg = Message.decode(data)
              reply = msg.process(self)
              if reply:
                  self.send(reply.encode())

      def store(self, name, data, callback):
          with self.lock:
              if not self.connected:
                  raise IOError('We are not connected to a server!')
              self.TRANS += 1
              self.callbacks[self.TRANS] = callback
              self.send(StoreRequest.marshal(self.TRANS, name, data).encode())

      def store_done(self, store_response):
          with self.lock:
              callback = self.callbacks[store_response.trans]
              del self.callbacks[store_response.trans]
          callback(store_response.name, store_response.status)

      def fetch(self, name, callback, error_cb):
          with self.lock:
              if not self.connected:
                  raise IOError('We are not connected to a server!')
              self.TRANS += 1
              self.callbacks[self.TRANS] = callback
              self.error_callbacks[self.TRANS] = error_cb
              self.send(FetchRequest(self.TRANS, name).encode())

      def fetch_done(self, fetch_response):
          with self.lock:
              error_cb = self.error_callbacks[fetch_response.trans]
              callback = self.callbacks[fetch_response.trans]
              del self.error_callbacks[fetch_response.trans]
              del self.callbacks[fetch_response.trans]
          if fetch_response.status != 0:
              error_cb(fetch_response.name, fetch_response.status)
          else:
              callback(*fetch_response.unmarshal())

Since we are dealing with asynchronous IO here, we will have a separate thread
performing all the brunt-work of receiving and sending. In order to be
thread-safe I chose to go with a split-phase design, where the user has to
specify a callback which is called as soon as the requested transaction is
completed. You could then strap this client into another event-driven
automaton.

Wrapping It Up
--------------
I hope you got the basic idea how you can create a client-server system in
about 300 lines of code, which is still easy to read and therefore to
maintain, debug and extend. If you're not convinced by the power of
``striptease`` try to imagine how this could have been implemented otherwise.
It is difficult to come up with a solution which is not cluttered with large
if-then-else cascades or has large bulky classes where the programmer needs to
implement several methods for decoding and encoding and dispatching. 

If I got you hooked for some experimentation, you can find the complete
example under ``examples/tutorial.py``, ready to toy around. Enjoy.
