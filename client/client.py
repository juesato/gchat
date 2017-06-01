#!/usr/bin/env python
# coding: UTF-8

# code extracted from nigiri

# Need to fix bug due to pressing enter twice
# May need to fix entering wrong pwd

import os
import datetime
import sys
import traceback
import re
import logging
import locale
import commands
import threading
import time
import random

import urwid
from urwid import MetaSignals

from client_api import Socket

# Uncomment for debug
# logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

log = open('log.txt', 'w')

class ExtendedListBox(urwid.ListBox):
    """
        Listbow widget with embeded autoscroll
    """

    __metaclass__ = urwid.MetaSignals
    signals = ["set_auto_scroll"]


    def set_auto_scroll(self, switch):
        if type(switch) != bool:
            return
        self._auto_scroll = switch
        urwid.emit_signal(self, "set_auto_scroll", switch)


    auto_scroll = property(lambda s: s._auto_scroll, set_auto_scroll)


    def __init__(self, body):
        urwid.ListBox.__init__(self, body)
        self.auto_scroll = True


    def switch_body(self, body):
        if self.body:
            urwid.disconnect_signal(body, "modified", self._invalidate)

        self.body = body
        self._invalidate()

        urwid.connect_signal(body, "modified", self._invalidate)


    def keypress(self, size, key):
        urwid.ListBox.keypress(self, size, key)

        if key in ("page up", "page down"):
            logging.debug("focus = %d, len = %d" % (self.get_focus()[1], len(self.body)))
            if self.get_focus()[1] == len(self.body)-1:
                self.auto_scroll = True
            else:
                self.auto_scroll = False
            logging.debug("auto_scroll = %s" % (self.auto_scroll))


    def scroll_to_bottom(self):
        logging.debug("current_focus = %s, len(self.body) = %d" % (self.get_focus()[1], len(self.body)))

        if self.auto_scroll:
            # at bottom -> scroll down
            self.set_focus(len(self.body)-1)



"""
 -------context-------
| --inner context---- |
|| HEADER            ||
||                   ||
|| BODY              ||
||                   ||
|| DIVIDER           ||
| ------------------- |
| FOOTER              |
 ---------------------
inner context = context.body
context.body.body = BODY
context.body.header = HEADER
context.body.footer = DIVIDER
context.footer = FOOTER
HEADER = Notice line (urwid.Text)
BODY = Extended ListBox
DIVIDER = Divider with information (urwid.Text)
FOOTER = Input line (Ext. Edit)
"""


class MainWindow(object):
    START = 0
    LOGIN = 1
    SIGNUP = 2
    SIGNUP_USERNAME = 3
    SIGNUP_PASSWORD = 4
    SIGNUP_EMAIL = 5
    SIGNUP_CONFIRMATION = 6
    LOGIN_PASSWORD = 7
    MAIN = 8

    __metaclass__ = MetaSignals
    signals = ["quit","keypress"]

    _palette = [
            ('divider','black','dark cyan', 'standout'),
            ('text','light gray', 'default'),
            ('bold_text', 'light gray', 'default', 'bold'),
            ("body", "text"),
            ("footer", "text"),
            ("header", "text"),
        ]

    for type, bg in (
            ("div_fg_", "dark cyan"),
            ("", "default")):
        for name, color in (
                ("red","dark red"),
                ("blue", "dark blue"),
                ("green", "dark green"),
                ("yellow", "yellow"),
                ("magenta", "dark magenta"),
                ("gray", "light gray"),
                ("white", "white"),
                ("black", "black")):
            _palette.append( (type + name, color, bg) )


    def __init__(self, sender="1234567890"):
        self.shall_quit = False
        self.sender = sender


    def main(self):
        """ 
            Entry point to start UI 
        """

        self.ui = urwid.raw_display.Screen()
        self.ui.register_palette(self._palette)
        self.state = MainWindow.START
        self.sock = Socket(self)
        self.build_interface()
        self.ui.run_wrapper(self.run)

    def run(self):
        """ 
            Setup input handler, invalidate handler to
            automatically redraw the interface if needed.
            Start mainloop.
        """

        # I don't know what the callbacks are for yet,
        # it's a code taken from the nigiri project
        def input_cb(key):
            if self.shall_quit:
                raise urwid.ExitMainLoop
            self.keypress(self.size, key)

        self.size = self.ui.get_cols_rows()

        self.main_loop = urwid.MainLoop(
                self.context,
                screen=self.ui,
                handle_mouse=False,
                unhandled_input=input_cb,
            )

        def call_redraw(*x):
            self.draw_interface()
            invalidate.locked = False
            return True

        inv = urwid.canvas.CanvasCache.invalidate

        def invalidate (cls, *a, **k):
            inv(*a, **k)

            if not invalidate.locked:
                invalidate.locked = True
                self.main_loop.set_alarm_in(0, call_redraw)

        invalidate.locked = False
        urwid.canvas.CanvasCache.invalidate = classmethod(invalidate)

        try:
            self.should_stop = False
            def refreshScreen(mainloop):
                return
                # while not self.should_stop:
                #     mainloop.draw_screen()
                #     time.sleep(0.2)
            self.refresh = threading.Thread(target=refreshScreen, args=(self.main_loop,))
            self.refresh.start()
            self.main_loop.run()
            # self.main_loop.run()

        except KeyboardInterrupt:
            self.sock.should_stop = True
            self.sock.listener.join()
            self.should_stop = True
            self.refresh.join()
            self.quit()


    def quit(self, exit=True):
        """ 
            Stops the ui, exits the application (if exit=True)
        """
        urwid.emit_signal(self, "quit")

        self.shall_quit = True

        if exit:
            log.close()
            sys.exit(0)


    def build_interface(self):
        """ 
            Call the widget methods to build the UI 
        """

        self.header = urwid.Text("Chat")
        self.footer = urwid.Edit("> ")
        self.divider = urwid.Text("Initializing.")

        self.generic_output_walker = urwid.SimpleListWalker([])
        self.body = ExtendedListBox(
            self.generic_output_walker)


        self.header = urwid.AttrWrap(self.header, "divider")
        self.footer = urwid.AttrWrap(self.footer, "footer")
        self.divider = urwid.AttrWrap(self.divider, "divider")
        self.body = urwid.AttrWrap(self.body, "body")

        self.footer.set_wrap_mode("space")

        main_frame = urwid.Frame(self.body, 
                                header=self.header,
                                footer=self.divider)
        
        self.context = urwid.Frame(main_frame, footer=self.footer)

        self.divider.set_text(("divider",
                               ("Send message:")))
        self.process_state()
        self.context.set_focus("footer")

    def process_state(self):
        if self.state == MainWindow.START:
            self.context.body.body = urwid.Filler(urwid.Text(""))
            self.divider.set_text(("divider", "type 'login' or 'signup' to start"))
        if self.state == MainWindow.SIGNUP:
            # self.context.body.body = urwid.Filler(urwid.Text("Enter your username below:"))
            self.divider.set_text(("divider", "Enter your username"))
        if self.state == MainWindow.SIGNUP_PASSWORD:
            self.context.body.body = urwid.Filler(urwid.Text(""))
            # self.context.body.body = urwid.Filler(urwid.Text("username: " + self.username))
            self.divider.set_text(("divider", "Make a password"))
        if self.state == MainWindow.LOGIN:
            self.context.body.body = urwid.Filler(urwid.Text("Enter your username below:"))
            self.divider.set_text(("divider", "Enter your username"))
        if self.state == MainWindow.LOGIN_PASSWORD:
            self.context.body.body = urwid.Filler(urwid.Text("username: " + self.username))
            self.divider.set_text(("divider", "Enter your password"))
        if self.state == MainWindow.SIGNUP_EMAIL:
            self.divider.set_text(("divider", "Enter your email address"))
        if self.state == MainWindow.SIGNUP_CONFIRMATION:
            self.divider.set_text(("divider", "Enter confirmation code sent to your email"))
        if self.state == MainWindow.MAIN:
            self.divider.set_text(("divider", 
                "Welcome, {0}!".format(self.username)))
            # 3 columns - chat, chat, contacts

            # placeholders
            self.status = ""
            self.avail = "available"
            self.contacts = []
            self.recipient = None
            # These should be headers rather than text fields
            self.recips = [None, None]
            self.active_recip = None
            self.friends = []
            self.chat_heads = [urwid.Text("Empty chat"), urwid.Text("Empty chat")]
            # self.chat_bodys = [urwid.Filler(urwid.Pile([]), valign='top'), \
            #                    urwid.Filler(urwid.Pile([]), valign='top')]
            self.chat_walkers = [urwid.SimpleListWalker([]), urwid.SimpleListWalker([])]
            self.chat_bodys = [ExtendedListBox(self.chat_walkers[0]), 
                               ExtendedListBox(self.chat_walkers[1])]
            self.chat_cols = [urwid.Frame(self.chat_bodys[0], header=self.chat_heads[0]), \
                              urwid.Frame(self.chat_bodys[1], header=self.chat_heads[1])]
            self.contacts_col = urwid.Filler(urwid.Text(self.username), valign='top')

            self.context.body.body = urwid.Columns([
                self.chat_cols[0], self.chat_cols[1], self.contacts_col], dividechars=3)
            self.main_loop.draw_screen()

    def is_friend(self, avail):
        if avail == "available" or avail == "offline":
            return True
        return False

    def update_status_col(self):
        s = '{0}\n{1}\n{2}\n'.format(
            self.username, self.avail, self.status)
        for contact in self.contacts:
            avail = self.contacts[contact]['avail']
            status = self.contacts[contact]['status']
            if self.is_friend(avail) and contact not in self.friends:
                self.friends.append(contact)
            s += '\n{0}\n{1}\n{2}\n'.format(
                contact, avail, status)

        # urwid.disconnect_signal(self.contacts_col.body, "modified", self.contacts_col.body._invalidate)
        # self.contacts_col.body = body
        self.contacts_col.body.set_text(('', s))
        # self.contacts_col.body._invalidate()
        # urwid.connect_signal(self.contacts_col.body, "modified", self.contacts_col.body._invalidate)

        self.main_loop.draw_screen()

    def accept_login(self):
        self.state = MainWindow.MAIN
        self.process_state()

    def reject_login(self):
        self.state = MainWindow.LOGIN
        self.process_state()

    def open_chat(self, user):
        if user not in self.friends:
            return
        try:
            self.active_recip = self.recips.index(user)
        except ValueError:
            updated_recips = self.recips[:]
            # (1 -> 2), fill 1
            if updated_recips[0]:
                updated_recips[1] = updated_recips[0]

            updated_recips[0] = user
            self.active_recip = 0
            self.update_open_chats(updated_recips)

        self.update_active_recip()
        pass

    def update_open_chats(self, recips):
        for i in xrange(len(recips)):
            if recips[i] is not self.recips[i]:
                self.recips[i] = recips[i]
                self.chat_heads[i].set_text(('text', recips[i]))
                # will update on callback
                msgs = self.sock.get_chat_log(recips[i])

    def update_active_recip(self):
        for i in xrange(len(self.recips)):
            recip = self.chat_cols[i]._header.get_text()[0]
            if '>> ' in recip:
                recip = recip.split('>> ')[1]
            self.chat_heads[i].set_text(('text', recip))
        i = self.active_recip
        recip = self.recips[i]
        self.chat_heads[i].set_text(('bold_text', '>> ' + recip))
        pass

    def debugCb(self, data):
        # log.write('debug\n')
        log.flush()

    def update_chat_log(self, data):
        log.write('\nupdate_chat_log ' + self.username + '\n')
        log.flush()
        try:
            recip = data['recip']
            chatlog = data['log']
        except KeyError:
            # no existing chat
            return
        # open the chat if it's not open yet
        if recip not in self.recips:
            self.open_chat(recip)
        else:
            self.active_recip = self.recips.index(recip)        
            self.update_active_recip()

        # add the messages to the chatbox
        for i in xrange(len(self.recips)):
            if recip != self.recips[i]:
                continue
            msg_widgets = []
            for m in chatlog:
                align = 'right' if m['sender'] == self.username else 'left'
                msg_widgets.append(urwid.Text(m['msg'], align=align))

            del self.chat_walkers[i].contents[:]
            for w in msg_widgets:
                self.chat_walkers[i].contents.append(w)
            self.chat_bodys[i].scroll_to_bottom()

        self.main_loop.draw_screen()

    def update_status(self, status):
        self.status = status
        self.sock.mainSocket.emit('status_update', status)

    def update_my_status(self, data):
        self.status = data

    def add_friend(self, user):
        self.sock.mainSocket.emit('friend_request', user)

    def send_confirmation_email(self, email):
        self.confirmation_key = random.randint(1000, 9999)
        self.sock.mainSocket.emit('email_confirmation', {
                'email': email,
                'key': str(self.confirmation_key)
            })

    def register_new_account(self):
        self.sock.mainSocket.emit('new_account', {
                'email': self.email,
                'username': self.username,
                'password': self.password
            })

    def send_chat(self, msg):
        try:
            receiver = self.recips[self.active_recip]
        except:
            return
        # log.write('send_chat' + str(self.active_recip) + str(self.recips) + self.recips[self.active_recip])
        log.write('send_chat' + receiver)
        log.flush()
        self.sock.mainSocket.emit('msg', {
            'username': self.username, 
            'msg': msg,
            'receiver': receiver
        })

        # Add it to your own view
        w = urwid.Text(msg, align='right')
        # w = (urwid.Text(msg, align='right'), ('pack', None))
        self.chat_walkers[self.active_recip].contents.append(w)
        self.chat_bodys[self.active_recip].scroll_to_bottom()

    def transition_state(self, text):
        old_state = self.state

        if self.state == MainWindow.START:
            if text == 'login':
                self.state = MainWindow.LOGIN
            if text == 'signup':
                self.state = MainWindow.SIGNUP
        elif self.state == MainWindow.SIGNUP:
            if text.strip():
                self.username = text
                self.state = MainWindow.SIGNUP_PASSWORD
        elif self.state == MainWindow.SIGNUP_PASSWORD:
            if text.strip():
                self.password = text
                self.state = MainWindow.SIGNUP_EMAIL
        elif self.state == MainWindow.SIGNUP_EMAIL:
            if text.strip():
                self.email = text
                self.send_confirmation_email(self.email)
                # send_confirmation_email(text)
                self.state = MainWindow.SIGNUP_CONFIRMATION
        elif self.state == MainWindow.SIGNUP_CONFIRMATION:
            if text.strip():
                if text == str(self.confirmation_key):
                    self.register_new_account()
                    self.state = MainWindow.START
        elif self.state == MainWindow.LOGIN:
            if text.strip():
                self.username = text
                self.state = MainWindow.LOGIN_PASSWORD
        elif self.state == MainWindow.LOGIN_PASSWORD:
            self.sock.login(self.username, text, self)
        elif self.state == MainWindow.MAIN:
            if text.startswith('\\chat'):
                user = text.split('\\chat')[1].strip()
                self.open_chat(user)
            elif text.startswith('\\status'):
                status = text.split('\\status')[1].strip()
                self.update_status(status)
            elif text.startswith('\\friend'):
                user = text.split('\\friend')[1].strip()
                self.add_friend(user)
            else:
                self.send_chat(text)

        if self.state != old_state:
            self.process_state()

    def draw_interface(self):
        self.main_loop.draw_screen()


    def keypress(self, size, key):
        """ 
            Handle user inputs
        """

        urwid.emit_signal(self, "keypress", size, key)

        # scroll the top panel
        if key in ("page up","page down"):
            self.body.keypress (size, key)

        # resize the main windows
        elif key == "window resize":
            self.size = self.ui.get_cols_rows()

        elif key in ("ctrl d", 'ctrl c'):
            self.quit()

        elif key == "enter":
            # Parse data or (if parse failed)
            # send it to the current world
            text = self.footer.get_edit_text()

            self.footer.set_edit_text(" "*len(text))
            self.footer.set_edit_text("")

            if text in ('quit', 'q'):
                self.quit()

            if text.strip():
                self.print_sent_message(text)
                self.print_received_message('Answer')
                self.transition_state(text)

        else:
            self.context.keypress (size, key)

 
    def print_sent_message(self, text):
        """
            Print a received message
        """

        self.print_text('[%s] You:' % self.get_time())
        self.print_text(text)
 
 
    def print_received_message(self, text):
        """
            Print a sent message
        """

        header = urwid.Text('[%s] System:' % self.get_time())
        header.set_align_mode('right')
        self.print_text(header)
        text = urwid.Text(text)
        text.set_align_mode('right')
        self.print_text(text)

        
    def print_text(self, text):
        """
            Print the given text in the _current_ window
            and scroll to the bottom. 
            You can pass a Text object or a string
        """

        walker = self.generic_output_walker

        if not isinstance(text, urwid.Text):
            text = urwid.Text(text)

        walker.append(text)

        self.body.scroll_to_bottom()


    def get_time(self):
        """
            Return formated current datetime
        """
        return datetime.datetime.now().strftime('%H:%M:%S')
        

def except_hook(extype, exobj, extb, manual=False):
    if not manual:
        try:
            main_window.quit(exit=False)
        except NameError:
            pass

    message = _("An error occured:\n%(divider)s\n%(traceback)s\n"\
        "%(exception)s\n%(divider)s" % {
            "divider": 20*"-",
            "traceback": "".join(traceback.format_tb(extb)),
            "exception": extype.__name__+": "+str(exobj)
        })

    logging.error(message)

    print >> sys.stderr, message


def setup_logging():
    """ set the path of the logfile to tekka.logfile config
        value and create it (including path) if needed.
        After that, add a logging handler for exceptions
        which reports exceptions catched by the logger
        to the tekka_excepthook. (DBus uses this)
    """
    try:
        class ExceptionHandler(logging.Handler):
            """ handler for exceptions caught with logging.error.
                dump those exceptions to the exception handler.
            """
            def emit(self, record):
                if record.exc_info:
                    except_hook(*record.exc_info)

        logfile = '/tmp/chat.log'
        logdir = os.path.dirname(logfile)

        if not os.path.exists(logdir):
            os.makedirs(logdir)

        logging.basicConfig(filename=logfile, level=logging.DEBUG,
            filemode="w")

        logging.getLogger("").addHandler(ExceptionHandler())

    except BaseException, e:
        print >> sys.stderr, "Logging init error: %s" % (e)


if __name__ == "__main__":
    setup_logging()

    main_window = MainWindow()

    sys.excepthook = except_hook

main_window.main()