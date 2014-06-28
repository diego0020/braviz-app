import zmq
import time
import sys
__author__ = 'Diego'

def start_server():
    context = zmq.Context()
    context.setsockopt(zmq.CONFLATE,1)
    listen_socket = context.socket(zmq.PULL)
    listen_socket.bind("tcp://127.0.0.1:*")
    listen_port = listen_socket.get_string(zmq.LAST_ENDPOINT)
    print listen_port
    forward_socket = context.socket(zmq.PUB)
    forward_socket.bind("tcp://127.0.0.1:*")
    forward_address = forward_socket.get_string(zmq.LAST_ENDPOINT)
    print forward_address
    sys.stdout.flush()
    for i in xrange(10):
        msg = listen_socket.recv()
        print msg
        forward_socket.send(msg)


def start_client():
    import zmq
    import sys
    context = zmq.Context()
    context.setsockopt(zmq.IMMEDIATE,1)
    send_socket = context.socket(zmq.PUSH)
    server_address = "tcp://127.0.0.1:63099"
    send_socket.connect(server_address)
    listen_socket = context.socket(zmq.SUB)
    listen_socket.connect("tcp://127.0.0.1:63101")
    listen_socket.setsockopt(zmq.SUBSCRIBE,"")
    zmq.eventloop.ioloop.install()
    def print_message(msg):
        print "received %s"%msg
        sys.stdout.flush()
    listen_stream = zmq.eventloop.zmqstream.ZMQStream(listen_socket)
    listen_stream.on_recv(print_message)
    i = 0
    def send_message():
        global i
        message = "message2 %d"%i
        i+=1
        print "sending", message
        sys.stdout.flush()
        try:
            status = send_socket.send(message,zmq.DONTWAIT)
        except zmq.Again:
            status = -1
        if status is not None:
            print "couldn't send message"
        print "done"
    periodic_sender = zmq.eventloop.ioloop.PeriodicCallback(send_message,1000)
    #periodic_sender.start()
    import datetime
    #zmq.eventloop.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(0,1),periodic_sender.start)
    zmq.eventloop.ioloop.IOLoop.instance().start()