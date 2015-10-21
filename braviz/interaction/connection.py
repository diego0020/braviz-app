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
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSignal
import threading
import logging
import time
import json
import numpy as np
import pandas as pd
import os
import datetime

__author__ = 'Diego'


class NpJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, pd.Int64Index):
            return o.to_native_types()
        elif isinstance(o, np.number):
            if isinstance(o, np.integer):
                o2 = int(o)
            else:
                o2 = float(o)
            return o2
        elif isinstance(o,datetime.datetime):
            return o.toordinal()
        else:
            try:
                o2 = [x for x in o]
            except TypeError:
                pass
            else:
                return o2
        return json.JSONEncoder.default(self, o)


class MessageServer(QtCore.QObject):
    """
    Acts as a message broker, listens for messages in one port, and broadcasts them in another port

    Also generates the *message_received* signal when it receives a message with the message string.
    The broadcast and receive addresses are binded to ephimeral ports, use the respective
    properties to query them.

    Args:
        local_only (bool) : If ``True`` the server will only accept connections from localhost

    """
    message_received = pyqtSignal(dict)

    def __init__(self, local_only=True):
        super(MessageServer, self).__init__()
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
        if zmq.zmq_version_info()[0] >= 4:
            context.setsockopt(zmq.IMMEDIATE, 1)
        base_address = "tcp://127.0.0.1" if self._local_only else "tcp://*"
        self._listen_socket = context.socket(zmq.PULL)
        self._listen_socket.bind("%s:*" % base_address)
        self._pull_address = self._listen_socket.get_string(zmq.LAST_ENDPOINT)
        self._forward_socket = context.socket(zmq.PUB)
        self._forward_socket.bind("%s:*" % base_address)
        self._pub_address = self._forward_socket.get_string(zmq.LAST_ENDPOINT)

        def server_loop():
            while not self._stop:
                net_msg = self._listen_socket.recv()
                if not self.__paused:
                    msg = json.loads(net_msg)
                    self.message_received.emit(msg)
                    self._forward_socket.send(net_msg)

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

    def send_message(self, msg):
        """
        Send a message in the broadcast address

        Args:
            msg (dict) : Message to broadcast, will be encoded as JSON
        """
        assert isinstance(msg, dict)
        net_msg = json.dumps(msg, cls=NpJSONEncoder)
        self._forward_socket.send(net_msg, zmq.DONTWAIT)

    def stop_server(self):
        """
        Stops the server thread
        """
        # atomic operation
        self._stop = True

    @property
    def pause(self):
        """
        Pause the server, received messages will be ignored.
        """
        return self.__paused

    @pause.setter
    def pause(self, val):
        self.__paused = bool(val)


class MessageClient(QtCore.QObject):
    """
    A client that connects to :class:`~braviz.interaction.connection.MessageServer`

    When it receives a message it emits the *message_received* signal with the message string.

    Args:
        server_broadcast (str) : Address of the server broadcast port
        server_receive (str) : Address of the server receive port
    """
    message_received = pyqtSignal(dict)

    def __init__(self, server_broadcast=None, server_receive=None):
        super(MessageClient, self).__init__()
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
        if zmq.zmq_version_info()[0] >= 4:
            context.setsockopt(zmq.IMMEDIATE, 1)
        if self._server_pull is not None:
            self._send_socket = context.socket(zmq.PUSH)
            server_address = self._server_pull
            self._send_socket.connect(server_address)
        if self._server_pub is not None:
            self._receive_socket = context.socket(zmq.SUB)
            self._receive_socket.connect(self._server_pub)
            self._receive_socket.setsockopt(zmq.SUBSCRIBE, "")

            def receive_loop():
                while not self._stop:
                    net_msg = self._receive_socket.recv()
                    # Ignore bouncing messages
                    if net_msg != self._last_message or (time.time() - self._last_send_time > 5):
                        msg = json.loads(net_msg)
                        self.message_received.emit(msg)
                        self._last_message = net_msg

            self._receive_thread = threading.Thread(target=receive_loop)
            self._receive_thread.setDaemon(True)
            self._receive_thread.start()

    def send_message(self, msg):
        """
        Send a message

        Args:
            msg (dict) : Message to send to the server, will be encoded as JSON
        """
        assert isinstance(msg, dict)
        assert "type" in msg

        log = logging.getLogger(__name__)

        if self._send_socket is None:
            log.error("Trying to send message without connection to server")
            return

        try:
            # self._send_socket.send(msg,zmq.DONTWAIT)
            net_msg = json.dumps(msg, cls=NpJSONEncoder)
            self._last_message = net_msg
            self._last_send_time = time.time()
            self._send_socket.send(net_msg, zmq.DONTWAIT)
        except zmq.Again:
            log.error("Couldn't send message %s", msg)

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
    method :meth:`get_last_message`

    Args:
        server_broadcast (str) : Address of the server broadcast port
        server_receive (str) : Address of the server receive port
    """

    def __init__(self, server_broadcast=None, server_receive=None):
        self._server_pub = server_broadcast
        self._server_pull = server_receive
        self._send_socket = None
        self._receive_socket = None
        self._receive_thread = None
        self._stop = False
        self._last_seen_message = ""
        self.connect_to_server()
        self._message_counter = 0
        self._last_send_time = -5

    def connect_to_server(self):
        """
        Connect to the server, called by the constructor
        """
        context = zmq.Context()
        if zmq.zmq_version_info()[0] >= 4:
            context.setsockopt(zmq.IMMEDIATE, 1)
        if self._server_pull is not None:
            self._send_socket = context.socket(zmq.PUSH)
            server_address = self._server_pull
            self._send_socket.connect(server_address)
        if self._server_pub is not None:
            self._receive_socket = context.socket(zmq.SUB)
            self._receive_socket.connect(self._server_pub)
            self._receive_socket.setsockopt(zmq.SUBSCRIBE, "")

            def receive_loop():
                while not self._stop:
                    net_msg = self._receive_socket.recv()
                    # Filter some messages to avoid loops
                    if net_msg != self._last_seen_message or (time.time() - self._last_send_time > 1):
                        self._last_seen_message = net_msg
                        self._message_counter += 1

            self._receive_thread = threading.Thread(target=receive_loop)
            self._receive_thread.setDaemon(True)
            self._receive_thread.start()

    def send_message(self, msg):
        """
        Send a message

        Args:
            msg (dict) : Message to send to the server
        """
        assert isinstance(msg, dict)
        log = logging.getLogger(__name__)

        if self._send_socket is None:
            log.error("Trying to send message without connection to server")
            return

        try:
            net_msg = json.dumps(msg, cls=NpJSONEncoder)
            self._last_seen_message = net_msg
            self._message_counter += 1
            self._last_send_time = time.time()
            self._send_socket.send(net_msg, zmq.DONTWAIT)
        except zmq.Again:
            log.error("Couldn't send message %s", msg)

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
        return self._message_counter, json.loads(self._last_seen_message)


class GenericMessageClient(object):
    """
    A client that connects to :class:`~braviz.interaction.connection.MessageServer`

    When it receives a message it calls ``handle_new_message`` on the handler,
    optionally, if the handler hast the ``handle_json_message``, it will be called with the
    raw json message as argument.

    Args:
        handler (object) : Must implement the ``handle_new_message`` method.
        server_broadcast (str) : Address of the server broadcast port
        server_receive (str) : Address of the server receive port
    """

    def __init__(self, handler, server_broadcast=None, server_receive=None):
        super(GenericMessageClient, self).__init__()
        self._server_pub = server_broadcast
        self._server_pull = server_receive
        self._send_socket = None
        self._receive_socket = None
        self._receive_thread = None
        self._stop = False
        self._last_message = None
        self._last_send_time = time.time()
        self.handler = handler
        self.connect_to_server()

    def connect_to_server(self):
        """
        Connect to the server, called by the constructor
        """
        context = zmq.Context()
        if zmq.zmq_version_info()[0] >= 4:
            context.setsockopt(zmq.IMMEDIATE, 1)
        if self._server_pull is not None:
            self._send_socket = context.socket(zmq.PUSH)
            server_address = self._server_pull
            self._send_socket.connect(server_address)
        if self._server_pub is not None:
            self._receive_socket = context.socket(zmq.SUB)
            self._receive_socket.connect(self._server_pub)
            self._receive_socket.setsockopt(zmq.SUBSCRIBE, "")

            def receive_loop():
                handles_json = hasattr(self.handler, "handle_json_message")
                while not self._stop:
                    net_msg = self._receive_socket.recv()
                    if handles_json:
                        self.handler.handle_json_message(net_msg)
                    else:
                        msg = json.loads(net_msg)
                        self.handler.handle_new_message(msg)

            self._receive_thread = threading.Thread(target=receive_loop)
            self._receive_thread.setDaemon(True)
            self._receive_thread.start()

    def send_message(self, msg):
        """
        Send a message

        .. Warning:: This message will also bounce to the handler, be careful with loops

        Args:
            msg (dict) : Message to send to the server
        """
        assert isinstance(msg, dict)
        log = logging.getLogger(__name__)

        if self._send_socket is None:
            log.error("Trying to send message without connection to server")
            return

        try:
            # self._send_socket.send(msg,zmq.DONTWAIT)
            net_msg = json.dumps(msg, cls=NpJSONEncoder)
            self._last_message = net_msg
            self._last_send_time = time.time()
            self._send_socket.send(net_msg, zmq.DONTWAIT)
        except zmq.Again:
            log.error("Couldn't send message %s", msg)

    def send_json_message(self, net_msg):
        """
        Send a message already encoded as json

        .. Warning:: This message will also bounce to the handler, be careful with loops

        Args:
            net_msg (str) : Message to send to the server
        """
        log = logging.getLogger(__name__)

        if self._send_socket is None:
            log.error("Trying to send message without connection to server")
            return

        try:
            # self._send_socket.send(msg,zmq.DONTWAIT)
            self._last_message = net_msg
            self._last_send_time = time.time()
            self._send_socket.send(net_msg)
        except zmq.Again:
            log.error("Couldn't send message %s", net_msg)

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


class BlockingMessageClient(object):
    """
    A listening client that connects to :class:`~braviz.interaction.connection.MessageServer`

    It blocks waiting for messages

    Args:
        server_broadcast (str) : Address of the server broadcast port
        server_receive (str) : Address of the server receive port, it is ignored
    """

    def __init__(self, server_broadcast, server_receive=None):
        super(BlockingMessageClient, self).__init__()
        self._server_pub = server_broadcast
        self._receive_socket = None
        self.connect_to_server()

    def connect_to_server(self):
        """
        Connect to the server, called by the constructor
        """
        context = zmq.Context()
        if zmq.zmq_version_info()[0] >= 4:
            context.setsockopt(zmq.IMMEDIATE, 1)

        self._receive_socket = context.socket(zmq.SUB)
        self._receive_socket.connect(self._server_pub)
        self._receive_socket.setsockopt(zmq.SUBSCRIBE, "")

    def get_message(self):
        net_msg = self._receive_socket.recv()
        msg = json.loads(net_msg)
        return msg

    @property
    def server_broadcast(self):
        """
        The server broadcast address
        """
        return self._server_pub


def create_log_message(action, next_state, application, uid):
    assert isinstance(action, basestring)
    assert isinstance(application, basestring)
    assert isinstance(next_state, dict)
    timestamp = time.time()
    msg = {
        "type": "log",
        "action": action,
        "state": next_state,
        "pid": uid,
        "application": application,
        "time": timestamp
    }
    return msg

def create_ready_message(instance_id):
    msg = {
        "type" : "ready",
        "source_pid" : os.getpid(),
        "source_id" : instance_id,
    }
    return msg