import zmq
import time
import sys
from PyQt4 import QtGui,QtCore
from  PyQt4.QtCore import pyqtSignal
import subprocess
import threading

__author__ = 'Diego'



class TestServer(QtGui.QMainWindow):
    message_received = pyqtSignal(basestring)
    def __init__(self):
        super(TestServer,self).__init__()
        layout = QtGui.QVBoxLayout()
        central = QtGui.QWidget()
        self.setCentralWidget(central)
        self.centralWidget().setLayout(layout)
        self.text_box = QtGui.QPlainTextEdit()
        self.check = QtGui.QCheckBox("Test")
        layout.addWidget(self.text_box)
        layout.addWidget(self.check)
        self.setWindowTitle("Test Server")
        self.stop = False
        self.listen_socket = None
        self.forward_socket = None
        self.pull_port = None
        self.pub_port = None
        self.server_thread = None
        self.start_server()
        self.messages = []
        self.message_received.connect(self.receive_message,QtCore.Qt.AutoConnection)
        self.nclientes = 0
        for i in xrange(2):
            self.launch_client()
        self.new_server_button = QtGui.QPushButton("new client")
        layout.addWidget(self.new_server_button)
        self.new_server_button.clicked.connect(self.launch_client)

    def start_server(self):
        context = zmq.Context()
        self.listen_socket = context.socket(zmq.PULL)
        self.listen_socket.bind("tcp://127.0.0.1:*")
        self.pull_port = self.listen_socket.get_string(zmq.LAST_ENDPOINT)
        self.forward_socket = context.socket(zmq.PUB)
        self.forward_socket.bind("tcp://127.0.0.1:*")
        self.pub_port = self.forward_socket.get_string(zmq.LAST_ENDPOINT)

        def server_loop():
            while not self.stop:
                msg = self.listen_socket.recv()
                print "SERVER RECEIVED %s"%msg
                self.message_received.emit(msg)
                self.forward_socket.send(msg)
        self.server_thread = threading.Thread(target=server_loop)
        self.server_thread.setDaemon(True)
        self.server_thread.start()

    def receive_message(self,msg):
        self.messages.append(msg)
        text = "\n".join(self.messages)
        self.text_box.setPlainText(text)

    def launch_client(self):
        client_name = "Client %d"%self.nclientes
        subprocess.Popen([sys.executable,__file__,client_name,self.pub_port,self.pull_port])
        self.nclientes += 1
        return

class TestClient(QtGui.QMainWindow):
    message_received = pyqtSignal(basestring)
    def __init__(self,name,server_pub,server_pull):
        super(TestClient,self).__init__()
        layout = QtGui.QVBoxLayout()
        central = QtGui.QWidget()
        self.setCentralWidget(central)
        self.centralWidget().setLayout(layout)
        self.text_box = QtGui.QPlainTextEdit()
        self.button = QtGui.QPushButton("Send Message")
        layout.addWidget(self.text_box)
        layout.addWidget(self.button)
        self.setWindowTitle(name)
        self.name = name
        self.server_pub = server_pub
        self.server_pull = server_pull
        self.send_socket = None
        self.receive_socket = None
        self.receive_thread = None
        self.connect_to_server()
        self.button.clicked.connect(self.send_message)
        self.message_received.connect(self.receive_message,QtCore.Qt.AutoConnection)
        self.number = 0
        self.messages = []

    def connect_to_server(self):
        context = zmq.Context()
        context.setsockopt(zmq.IMMEDIATE,1)
        self.send_socket = context.socket(zmq.PUSH)
        server_address = self.server_pull
        self.send_socket.connect(server_address)
        self.receive_socket = context.socket(zmq.SUB)
        self.receive_socket.connect(self.server_pub)
        self.receive_socket.setsockopt(zmq.SUBSCRIBE,"")
        def receive_loop():
            while True:
                msg = self.receive_socket.recv()
                msg2 = "%d: %s"%(self.number,msg)
                self.number += 1
                print "%s RECEIVED %s"%(self.name,msg2)
                self.message_received.emit(msg2)
        self.receive_thread = threading.Thread(target=receive_loop)
        self.receive_thread.setDaemon(True)
        self.receive_thread.start()

    def send_message(self):
        msg = "Hello from %s"%self.name
        try:
            self.send_socket.send(msg,zmq.DONTWAIT)
        except zmq.Again:
            print "Server disconnected"

    def receive_message(self,msg):
        self.messages.append(msg)
        text = "\n".join(self.messages)
        self.text_box.setPlainText(text)


if __name__ == "__main__":
    import sys
    args = sys.argv
    app = QtGui.QApplication([])
    if len(args) == 1:
        main_window = TestServer()
    else:
        main_window = TestClient(sys.argv[1],sys.argv[2],sys.argv[3])
    main_window.show()
    app.exec_()