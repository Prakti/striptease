#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division

import sys
import socket
import marshal
import asyncore
import threading

from base64 import b64encode, b64decode
from striptease import Struct, uint8, uint16, String

if sys.version_info.major < 3:
    import gdbm as gnudbm
    bytes = str
else:
    import dbm.gnu as gnudbm


class Decoder(type):
    """
    Metaclass for registering all messages with their msgid in a central
    registry. This is used by the class Message to dispatch the decoding to
    the appropriate subclass
    """

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


class StoreRequest(Message):
    """
    StoreRequest Message for storing 'data' at the server under 'name'
    """

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


class FetchRequest(Message):
    """
    Sent to fetch data from the server, stored by 'name'
    """

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
    """
    Sent in response to a FetchRequest, containing the data requested by
    'name'
    """

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


def hexdump(strng):
    return "".join("%X" %(ord(c)) for c in strng)


def print_store_done(name, status):
    if status > 0:
        print("Could not store ", name, ". Err#: ", status)
    else:
        print(name, " stored successfully.")


def print_fetch_success(name, data):
    print("Fetched: ", name, " = ", data)


def print_fetch_fail(name, status):
    print("Could not fetch ", name, ". Err#: ", status)


def start_server(host, port):
    serv = StorageServer(host, port)
    asyncore.loop()


def start_client(host, port):
    client = StorageClient(host, port)
    loop = threading.Thread(target=asyncore.loop)
    loop.start()
    return client, loop


class ClientTestrun():

    def __init__(self):
        print('Waiting for Connection', end='')
        self.client, loop = start_client('localhost', 4711)
        while not self.client.connected:
            print('.', end='')
        print('connected')

    def store_done(self, name, status):
        print_store_done(name, status)
        if status == 0:
            self.client.fetch(name, self.fetch_success, self.fetch_fail)

    def fetch_success(self, name, data):
        print_fetch_success(name, data)
        sys.exit(0)

    def fetch_fail(self, name, status):
        print_fetch_fail(name, dataus)
        sys.exit(1)

    def __call__(self):
        data = [1,2,3]
        self.client.store('foo', data, self.store_done)


def server_testrun():
    print("Starting Server")
    start_server('localhost', 4711)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == 'server':
            server_testrun()
        elif sys.argv[1] == 'client':
            client_testrun = ClientTestrun()
            client_testrun()
        else:
            print("Please specify either 'client' or 'server' mode.")


if __name__ == '__main__':
    main()

