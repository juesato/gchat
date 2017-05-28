from socketIO_client import SocketIO
import json
import time
import threading

IP_ADDR = "52.41.108.183"

class Socket():
    def __init__(self, mainWindow):
        self.log = open('api_log.txt', 'w')
        self.mainSocket = SocketIO(IP_ADDR, 80, verify=False)
        self.mainWindow = mainWindow
        self.should_stop = False
        self.listener = threading.Thread(target=self.poll)
        self.log.write('hello\n')
        self.log.flush()
        self.listener.start()
        # self.poll()

    def send(msg):
        self.mainSocket.emit('message', msg, self.on_msg_response)

    def on_msg_response(self, *args):
        self.log.write('GOT RESPONSE: ' + str(args))

    def login(self, user, passwd, mainWindow):
        self.log.write('Make req\n')
        self.log.flush()
        self.mainSocket.emit('login', json.dumps({
                'username': user,
                'password': passwd
            }))

        self.log.write('A\n')
        self.log.flush()
        # self.mainSocket.on('login_auth', cb)
        self.mainSocket.on('login_auth', self.process_auth)
        # I have no clue why it's wait instead of wait_for_callback
        # self.mainSocket.wait(seconds=2.0)

    def poll(self):
        # This is such a poorly designed callback system. I'm so upset
        self.mainSocket.on('login_auth', self.process_auth)
        self.mainSocket.on('contacts', self.get_contacts)
        self.mainSocket.on('chat', self.new_msg)
        while not self.should_stop:
            self.log.write('waiting...\n')
            self.log.flush()
            self.mainSocket.wait(seconds=2.0)

    def process_auth(self, *args):
        self.log.write('process\n')
        self.log.flush()
        if not len(args) or not args:
            self.mainWindow.reject_login()
            return
        self.mainWindow.accept_login()

    def get_contacts(self, *args):
        self.log.write('contacts!!\n')
        self.log.flush()

    def new_msg(self, *args):
        pass
