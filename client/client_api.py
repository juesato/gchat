from socketIO_client import SocketIO
import json
import time
import threading

IP_ADDR = "52.41.108.183"

DEBUG = False

class Socket():
    def __init__(self, mainWindow):
        if DEBUG:
            self.log = open('api_log.txt', 'w')
        self.mainSocket = SocketIO(IP_ADDR, 80, verify=False)
        self.mainWindow = mainWindow
        self.should_stop = False
        self.listener = threading.Thread(target=self.poll)
        self.listener.start()
        # self.poll()

    def debug(self, msg):
        if DEBUG:
            self.log.write(msg)
            self.log.write('\n')
            self.log.flush()

    def get_chat_log(self, handle):
        self.mainSocket.emit('history', {
                'username': self.mainWindow.username,
                'recip': handle
            })

    def login(self, user, passwd, mainWindow):
        self.debug('Make req')
        self.mainSocket.emit('login', json.dumps({
                'username': user,
                'password': passwd
            }))

        self.mainSocket.on('login_auth', self.process_auth)

    def poll(self):
        # This is such a poorly designed callback system. I'm so upset
        self.mainSocket.on('history', self.mainWindow.update_chat_log)
        self.mainSocket.on('login_auth', self.process_auth)
        self.mainSocket.on('contacts', self.get_contacts)
        self.mainSocket.on('chat', self.new_msg)
        self.mainSocket.on('friend_status', self.update_friend_status)
        self.mainSocket.on('my_status', self.mainWindow.update_my_status)
        self.mainSocket.on('debug', self.mainWindow.debugCb)
        while not self.should_stop:
            self.debug('waiting...')
            self.mainSocket.wait(seconds=2.0)

    def process_auth(self, *args):
        if not len(args) or not args:
            self.mainWindow.reject_login()
            return
        self.mainWindow.accept_login()

    def get_contacts(self, *args):
        self.debug('contacts!! ' + str(args))
        
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
