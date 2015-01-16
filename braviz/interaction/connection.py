##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


import zmq
from PyQt4 import QtGui,QtCore
from  PyQt4.QtCore import pyqtSignal
import threading
import logging
import time

__author__ = 'Diego'


class MessageServer(QtCore.QObject):
    """
    Acts as a message broker, listens for messages in one port, and broadcasts them in another port

    Also generates the *message_received* signal when it receives a message with the message string.
    The broadcast and receive addresses are binded to ephimeral ports, use the respective
    properties to query them.

    Args:
        local_only (bool) : If ``True`` the server will only accept connections from localhost

    """
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
        self.__paused = False
        self.start_server()

    def start_server(self):
        """
        Starts the server thread, called by the constructor
        """
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
                if not self.__paused:
                    self.message_received.emit(msg)
                    self._forward_socket.send(msg)
        self._server_thread = threading.Thread(target=server_loop)
        self._server_thread.setDaemon(True)
        self._server_thread.start()

    @property
    def broadcast_address(self):
        """
        The address in which this server broadcasts messages
        """
        return self._pub_address

    @property
    def receive_address(self):
        """
        The address in which the server listens for messages
        """
        return self._pull_address

    def send_message(self,msg):
        """
        Send a message in the broadcast address

        Args:
            msg (str) : Message to broadcast
        """
        self._forward_socket.send(msg)

    def stop_server(self):
        """
        Stops the server thread
        """
        #atomi operation
        self._stop = True

    @property
    def pause(self):
        """
        Pause the server, received messages will be ignored.
        """
        return self.__paused

    @pause.setter
    def pause(self,val):
        self.__paused = bool(val)


class MessageClient(QtCore.QObject):
    """
    A client that connects to :class:`~braviz.interaction.connection.MessageServer`

    When it receives a message it emits the *message_received* signal with the message string.

    Args:
        server_broadcast (str) : Address of the server broadcast port
        server_receive (str) : Address of the server receive port
    """
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
        self._last_send_time = -5
        self.connect_to_server()


    def connect_to_server(self):
        """
        Connect to the server, called by the constructor
        """
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
                    #Ignore bouncing messages
                    if msg != self._last_message or (time.time() - self._last_send_time > 5):
                        self.message_received.emit(msg)
                        self._last_message = msg
            self._receive_thread = threading.Thread(target=receive_loop)
            self._receive_thread.setDaemon(True)
            self._receive_thread.start()

    def send_message(self,msg):
        """
        Send a message

        Args:
            msg (str) : Message to send to the server
        """
        log = logging.getLogger(__file__)

        if self._send_socket is None:
            log.error("Trying to send message without connection to server")
            return

        try:
            #self._send_socket.send(msg,zmq.DONTWAIT)
            self._last_message = msg
            self._last_send_time = time.time()
            self._send_socket.send(msg)
        except zmq.Again:
            log.error("Couldn't send message %s",msg)

    def stop(self):
        """
        stop the client
        """
        self._stop = True

    @property
    def server_broadcast(self):
        """
        The server broadcast address
        """
        return self._server_pub

    @property
    def server_receive(self):
        """
        The server receive address
        """
        return self._server_pull


class PassiveMessageClient(object):
    """
    A client that connects to :class:`~braviz.interaction.connection.MessageServer`

    When it receives a message it keeps it in memory. The last message may be polled using the
    method :meth:`PassiveMessageClient.get_last_message`

    Args:
        server_broadcast (str) : Address of the server broadcast port
        server_receive (str) : Address of the server receive port
    """

    def __init__(self,server_broadcast=None,server_receive=None):
        self._server_pub = server_broadcast
        self._server_pull = server_receive
        self._send_socket = None
        self._receive_socket = None
        self._receive_thread = None
        self._stop = False
        self._last_seen_message = None
        self.connect_to_server()
        self._message_counter = 0
        self._last_received_message = ""
        self._last_send_time = -5


    def connect_to_server(self):
        """
        Connect to the server, called by the constructor
        """
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
                    #Filter some messages to avoid loops
                    if msg != self._last_seen_message or (time.time() - self._last_send_time > 5):
                        self._last_seen_message = msg
                        self._last_received_message = msg
                        self._message_counter += 1
            self._receive_thread = threading.Thread(target=receive_loop)
            self._receive_thread.setDaemon(True)
            self._receive_thread.start()

    def send_message(self,msg):
        """
        Send a message

        Args:
            msg (str) : Message to send to the server
        """
        log = logging.getLogger(__file__)

        if self._send_socket is None:
            log.error("Trying to send message without connection to server")
            return

        try:
            self._last_seen_message = msg
            self._last_send_time = time.time()
            self._send_socket.send(msg)
        except zmq.Again:
            log.error("Couldn't send message %s",msg)

    def stop(self):
        """
        stop the client
        """
        self._stop = True

    @property
    def server_broadcast(self):
        """
        The server broadcast address
        """
        return self._server_pub

    @property
    def server_receive(self):
        """
        The server receive address
        """
        return self._server_pull

    def get_last_message(self):
        """
        Get the last received message and a consecutive number

        Returns:
            ``number, message_text``; where the number will increase each time a new message arrives
        """
        return self._message_counter,self._last_received_message