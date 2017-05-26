import urwid

mainLoop = urwid.MainLoop(urwid.Text('Gchat'), palette=[('reversed', 'standout', '')])

class ActionButton(urwid.Button):
    def __init__(self, caption, callback):
        super(ActionButton, self).__init__("")
        urwid.connect_signal(self, 'click', callback)
        self._w = urwid.AttrMap(urwid.SelectableIcon(caption, 1),
            None, focus_map='reversed')

class Option(urwid.WidgetWrap):
    def __init__(self, name, choices):
        super(Option, self).__init__(
            ActionButton([u" > go to ", name], self.select_option))
        self.heading = urwid.Text([u"\nLocation: ", name, "\n"])
        self.choices = choices
        # create links back to ourself
        for child in choices:
            getattr(child, 'choices', []).insert(0, self)

    def select_option(self, button):
        app.update(self)

class Thing(urwid.WidgetWrap):
    def __init__(self, name):
        super(Thing, self).__init__(
            ActionButton([u" * take ", name], self.take_thing))
        self.name = name

    def take_thing(self, button):
        self._w = urwid.Text(u" - %s (taken)" % self.name)
        app.take_thing(self)

def exit_program():
    raise urwid.ExitMainLoop()

# map_top = Option(u'Welcome!', [
#     Option(u'Log in', [
#         Option(u'refrigerator', []),
#         Option(u'cupboard', [
#             Thing(u'jug'),
#         ]),
#     ]),
#     Option(u'Sign up', [
#         Option(u'tree', [
#             Thing(u'lemon'),
#             Thing(u'bird'),
#         ]),
#     ]),
# ])

def show(widget):
    def callback(button):
        mainLoop.widget = widget
    return callback

login = urwid.Text("Login screen")
signup = urwid.Text("Signup screen")

start = urwid.Pile([
    ActionButton('Log in', show(login)),
    ActionButton('Sign up', show(signup))
        ])

class App(object):
    def __init__(self):
        self.log = urwid.SimpleFocusListWalker([start])
        self.top = urwid.ListBox(self.log)

app = App()
mainLoop.widget = app.top
mainLoop.run()
# from curses import wrapper
# try:
#     def main(scr):
#         mainLoop.run()
#     wrapper(main)
# except Exception as e:
#     print (e)
#     exit_program()