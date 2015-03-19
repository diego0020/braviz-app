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

from __future__ import print_function
import logging
import tornado.web

from tornado.concurrent import Future
import tornado.gen


__author__ = 'diego'


class MessageHandler(tornado.web.RequestHandler):

    """
    Allow querying for messages and sending messages through http

    **GET** requests will receive json data ``{"count":<n>,"message",<s>}`` where count is a number
     that increases with any new message, and message is the text of the last message.

    **POST** requests allow to send messages. It is required to have a ``"message"`` parameter in the
    request body
    """

    def __init__(self, application, request, **kwargs):
        super(MessageHandler, self).__init__(application, request, **kwargs)

    def initialize(self, message_client):
        """
        Requires a :class:`braviz.interaction.connection.PassiveMessageClient`
        """
        self.message_client = message_client
        super(MessageHandler, self).initialize()

    def get(self, *args, **kwargs):
        if self.message_client is None:
            self.write("")
        else:
            i, m = self.message_client.get_last_message()
            self.write({"count": i, "message": m})

    def post(self, *args, **kwargs):
        if self.message_client is None:
            self.write_error(503)
        else:
            m = str(self.get_body_argument("message"))
            self.message_client.send_message(m)
        self.set_status(202, "Message sent")


class MessageFutureProxy(object):

    """
    Interfaces tornado futures with zmq messages
    """
    # Based on
    # https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py

    def __init__(self,):
        self.waiters = set()

    def wait_for_message(self):
        msg_future = Future()
        self.waiters.add(msg_future)
        print("holding %d requests"%len(self.waiters))
        return msg_future

    def cancel_wait(self, future):
        self.waiters.remove(future)

    def handle_new_message(self, msg):
        for future in self.waiters:
            future.set_result(msg)
        self.waiters.clear()


class LongPollMessageHandler(tornado.web.RequestHandler):

    """
    Allow querying for messages and sending messages through http

    **GET** requests will receive json data ``{"message",<s>}``. This request will not return until a new
    message is available. (Long poll)

    **POST** requests allow to send messages. It is required to have a ``"message"`` parameter in the
    request body
    """

    def __init__(self, application, request, **kwargs):
        super(LongPollMessageHandler, self).__init__(
            application, request, **kwargs)

    def initialize(self, message_client):
        """
        Requires a :class:`braviz.interaction.connection.GenericMessageClient` with
        :class:`braviz.interaction.tornado_connection.MessageFutureProxy` as handler
        """
        self.message_client = message_client
        self.message_handler = message_client.handler
        super(LongPollMessageHandler, self).initialize()

    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        self.future = self.message_handler.wait_for_message()
        msg = yield self.future
        if self.request.connection.stream.closed():
            print("stream closed")
            return
        print("sending response")
        self.write({"message": msg})

    def on_connection_close(self):
        self.message_handler.cancel_wait(self.future)

    def post(self, *args, **kwargs):
        if self.message_client is None:
            self.write_error(503)
        else:
            m = str(self.get_body_argument("message"))
            self.message_client.send_message(m)
        self.set_status(202, "Message sent")
