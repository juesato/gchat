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
        self.mainSocket.on('friend_status', self.update_friend_status)
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
        self.log.write(str(args))
        self.log.flush()
        
        contacts = {}
        for c in args[0]:
            name = c['username']
            rel = c['relation']
            contacts[name] = {}
            if rel == 'friends':
                # placeholder
                contacts[name]['avail'] = 'offline'
                contacts[name]['status'] = ''
                self.mainSocket.emit('friend', name)
            else:
                contacts[name]['avail'] = rel
                contacts[name]['status'] = ''

        self.mainWindow.contacts = contacts
        self.mainWindow.update_status_col()

    def update_friend_status(self, *args):
        name   = args[0]['username']
        status = args[0]['status']
        avail  = args[0]['avail']
        self.mainWindow.contacts[name]['status'] = status
        self.mainWindow.contacts[name]['avail'] = avail
        self.mainWindow.update_status_col()

    def new_msg(self, *args):
        pass
