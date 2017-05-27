from socketIO_client import SocketIO
import json
import time

IP_ADDR = "52.41.108.183"

class Socket():
    def __init__(self):
        self.log = open('api_log.txt', 'w')
        self.mainSocket = SocketIO(IP_ADDR, 80, verify=False)
        # self.mainSocket.emit('message', 'WORLD', self.on_msg_response)

    def send(msg):
        self.mainSocket.emit('message', msg, self.on_msg_response)

    def on_msg_response(self, *args):
        self.log.write('GOT RESPONSE: ' + str(args))

    def login(self, user, passwd, mainWindow):
        self.log.write('Make req\n')
        self.log.flush()
        def cb(*args):
            if not len(args) or not args:
                mainWindow.reject_login()
                return
            mainWindow.accept_login()

        self.mainSocket.emit('login', json.dumps({
                'username': user,
                'password': passwd
            }), cb)
        self.mainSocket.on('login_auth', cb)

        # This is such a poorly designed callback system I'm so upset
        self.mainSocket.wait_for_callbacks(seconds=2)
