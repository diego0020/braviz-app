import zmq
from PyQt4 import QtGui,QtCore
from  PyQt4.QtCore import pyqtSignal
import threading
import logging

__author__ = 'Diego'


class MessageServer(QtCore.QObject):
    message_received = pyqtSignal(basestring)
    def __init__(self,local_only = True):
        super(MessageServer,self).__init__()
        self._stop = False
        self._listen_socket = None
        self._forward_socket = None
        self._pull_address = None
        self._pub_address = None
        self._server_thread = None
        self._local_only = local_only
        self.start_server()

    def start_server(self):
        context = zmq.Context()
        if zmq.zmq_version_info()[0]>=4:
            context.setsockopt(zmq.IMMEDIATE,1)
        base_address = "tcp://127.0.0.1" if self._local_only else "tcp://*"
        self._listen_socket = context.socket(zmq.PULL)
        self._listen_socket.bind("%s:*"%base_address)
        self._pull_address = self._listen_socket.get_string(zmq.LAST_ENDPOINT)
        self._forward_socket = context.socket(zmq.PUB)
        self._forward_socket.bind("%s:*"%base_address)
        self._pub_address = self._forward_socket.get_string(zmq.LAST_ENDPOINT)

        def server_loop():
            while not self._stop:
                msg = self._listen_socket.recv()
                self.message_received.emit(msg)
                self._forward_socket.send(msg)
        self._server_thread = threading.Thread(target=server_loop)
        self._server_thread.setDaemon(True)
        self._server_thread.start()

    @property
    def broadcast_address(self):
        return self._pub_address

    @property
    def receive_address(self):
        return self._pull_address

    def send_message(self,msg):
        self._forward_socket.send(msg)

    def stop_server(self):
        #atomi operation
        self._stop = True


class MessageClient(QtCore.QObject):
    message_received = pyqtSignal(basestring)
    def __init__(self,server_broadcast=None,server_receive=None):
        super(MessageClient,self).__init__()
        self._server_pub = server_broadcast
        self._server_pull = server_receive
        self._send_socket = None
        self._receive_socket = None
        self._receive_thread = None
        self._stop = False
        self._last_message = None
        self.connect_to_server()


    def connect_to_server(self):
        context = zmq.Context()
        if zmq.zmq_version_info()[0]>=4:
            context.setsockopt(zmq.IMMEDIATE,1)
        if self._server_pull is not None:
            self._send_socket = context.socket(zmq.PUSH)
            server_address = self._server_pull
            self._send_socket.connect(server_address)
        if self._server_pub is not None:
            self._receive_socket = context.socket(zmq.SUB)
            self._receive_socket.connect(self._server_pub)
            self._receive_socket.setsockopt(zmq.SUBSCRIBE,"")
            def receive_loop():
                while not self._stop:
                    msg = self._receive_socket.recv()
                    if msg != self._last_message:
                        self.message_received.emit(msg)
                        self._last_message = msg
            self._receive_thread = threading.Thread(target=receive_loop)
            self._receive_thread.setDaemon(True)
            self._receive_thread.start()

    def send_message(self,msg):
        log = logging.getLogger(__file__)

        if self._send_socket is None:
            log.error("Trying to send message without connection to server")
            return

        try:
            #self._send_socket.send(msg,zmq.DONTWAIT)
            self._last_message = msg
            self._send_socket.send(msg)
        except zmq.Again:
            log.error("Couldn't send message %s",msg)

    def stop(self):
        self._stop = True

    @property
    def server_broadcast(self):
        return self._server_pub

    @property
    def server_receive(self):
        return self._server_pull