from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup


class DialogueBox(Popup):
    text = StringProperty()

    def __init__(self, text, name, **kwargs):
        self.text = text
        self.name = name
        super(DialogueBox, self).__init__(**kwargs)


class NavButton(Button):
    pass


class Notification(Popup):
    message = StringProperty('Hi.')
    pass