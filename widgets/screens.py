import fnmatch
import os

from kivy.app import App
from kivy.properties import ObjectProperty, Clock, StringProperty
from kivy.uix.screenmanager import Screen

from helpers import SAVE_PATH
from widgets.ui import NavButton


class TitleMenu(Screen):
    pass


class NewGame(Screen):
    pass


class LoadGame(Screen):
    save_path = StringProperty(SAVE_PATH)

    def on_enter(self, *args):
        self.ids.save_choices.clear_widgets()
        for rootdir, dir, files in os.walk(SAVE_PATH):
            for current_file in sorted(fnmatch.filter(files, "*.save")):
                self.ids.save_choices.add_widget(NavButton(
                    text=os.path.splitext(current_file)[0],
                    on_release=lambda *args : App.get_running_app().load_game(SAVE_PATH + current_file)))


class Game(Screen):
    scroller = ObjectProperty()

    def __init__(self, *args, **kwargs):
        super(Game, self).__init__(**kwargs)
        print('game init hit')
        Clock.schedule_interval(self.set_fps, .2)

    def set_fps(self, *args):
        # print('set fps hit')
        self.ids.counter.text = str(round(Clock.get_fps(), 2))

