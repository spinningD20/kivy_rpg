# import cProfile
import fnmatch
import gc
import os

from kivy.config import Config


# # # # #

Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '720')  # for testing scale

# # # # #

from dbfunctions import all_tmx_files_to_db

from helpers import runpath, SAVE_PATH, keys
from widgets.screens import Game, TitleMenu, NewGame, LoadGame
from widgets.tilemap import TileMapWidget
from widgets.ui import Notification

from kivy.app import App
from kivy.core.window import Window
from kivy.properties import ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.utils import platform
from shutil import copyfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import TileMap, MapObject, GameFlag
from genericpath import exists


class GameApp(App):
    manager = ObjectProperty()
    title_menu = ObjectProperty()
    game = ObjectProperty()
    overlay = ObjectProperty()
    current_instance = None

    def __init__(self, **kwargs):
        super(GameApp, self).__init__(**kwargs)
        print('app init')
        Window.bind(on_resize=self.resize)

    #
    # def on_start(self):
    #     self.profile = cProfile.Profile()
    #     self.profile.enable()
    #
    #
    # def on_stop(self):
    #     self.profile.disable()
    #     self.profile.dump_stats('myapp.profile')

    def resize(self, window, x, y):
        print('resize on app')
        self.set_scale()
        #
        # if self.current_instance:
        #     self.current_instance.map.resize_view(x, y)

    def set_scale(self):
        if self.manager.current_screen.ids.get('scalar'):
            scale_amount = Window.size[0] / 233
            print('scaling factor', scale_amount)
            animation = Animation(scale=scale_amount, duration=.2)
            scalar = self.manager.current_screen.ids.scalar
            # TODO - when we resize the screen, we want to focus on the map's focus target coordinates in the Scalar
            scalar.center = scalar.parent.center
            self.current_instance.map.recenter(*Window.size)
            animation.start(scalar)

    def reseed(self):
        # this will only work if app has permission to modify seed.db, for example NOT IOS.
        # PS) hopefully it's obvious that this will only effect new games based off of new seed.db.
        # all_tmx_files_to_db will just update seed.db if it exists, but for now, just wipe the slate clean to be sure
        if exists('seed.db'):
            print('deleting seed.db, existing...')
            os.remove('seed.db')
        all_tmx_files_to_db()
        Notification(message='Reseed complete!').open()

    def new_game(self, choice='clyde'):
        print('new game')
        # get numbers of last save files to find an appropriate save file id to provide copying
        # make this beast a lot shorter sometime soon.  Probably just iterate over files with choice in them, inc
        # all_tmx_files_to_db() # update seed file for any changes from tmx files before copying it to use
        save_number = 0
        for rootdir, dir, files in os.walk(SAVE_PATH):
            current_number = len(fnmatch.filter(files, choice + '*.save'))
            if current_number > save_number:
                save_number = current_number
        save_number += 1
        filename = choice + '-' + str(save_number)
        while os.path.isfile(SAVE_PATH + filename + '.save'):
            filename += '0'
        filename = SAVE_PATH + filename + '.save'
        # copy seed db file with name of filename to make a new save file
        copyfile(os.path.join(runpath, 'seed.db'), filename)
        engine = create_engine('sqlite:///' + filename)
        Session = sessionmaker(bind=engine)  # configure session object
        self.db = Session()
        # set player flags like main_character, player_party, etc
        player_character_flag = self.db.query(GameFlag).filter(GameFlag.name == 'player_character').first()
        if not player_character_flag:
            player_character_flag = GameFlag()
            player_character_flag.name = 'player_character'
        player_character_flag.value = choice
        # MAYBE TO-DO : find clyde map object and set its coords and map_id to values for clyde choice?
        # FOR NOW, commit changes
        self.db.add(player_character_flag)
        self.db.commit()
        print('save file created...loading', filename)
        self.load_game(filename)

    def load_game(self, filename=os.path.join(runpath, 'seed.db')):
        print('hitting load game')
        # set the db here, get current map player object was last at, and load that map
        engine = create_engine('sqlite:///' + filename)
        Session = sessionmaker(bind=engine)  # configure session object
        self.db = Session()
        # until the other characters are in the db, trying to load a game with anyone but clyde will crash
        player_character_flag = self.db.query(GameFlag).filter(GameFlag.name == 'player_character').first()
        self.player_object = self.db.query(MapObject).filter(MapObject.name == player_character_flag.value).first()
        tilemap = self.db.query(TileMap).filter(TileMap.id == self.player_object.map_id).first()
        self.manager.current = 'Game'
        self.load_map(tilemap.file_name)

    def load_map(self, map_name, *args):
        if self.current_instance is not None:
            self.current_instance.stop()
        self.current_instance = None
        gc.collect()
        tilemap = self.db.query(TileMap).filter(TileMap.file_name == map_name).first()
        self.current_instance = TileMapWidget(tilemap)
        Clock.schedule_once(self.current_instance.start, .15)
        Clock.schedule_once(lambda *args: self.game.ids.container.add_widget(self.current_instance), .2)
        Clock.schedule_once(lambda *args: self.set_scale(), .2)

    def build(self):
        self.manager = ScreenManager()
        self.manager.transition = FadeTransition(duration=.25)
        self.game = Game()
        for screen in [TitleMenu(), NewGame(), LoadGame(), self.game]:
            self.manager.add_widget(screen)
        self.manager.current = 'TitleMenu'
        self.overlay = FloatLayout()
        self.overlay.add_widget(self.manager)
        return self.overlay

    # def on_start(self):
    #     self.profile = cProfile.Profile()
    #     self.profile.enable()
    #
    # def on_stop(self):
    #     self.profile.disable()
    #     self.profile.dump_stats('myapp.profile')


if __name__ == '__main__':
    if platform != 'android':
        def on_key_down(window, keycode, *rest):
            keys[keycode] = True


        def on_key_up(window, keycode, *rest):
            keys[keycode] = False


        Window.bind(on_key_down=on_key_down, on_key_up=on_key_up)
    GameApp().run()
