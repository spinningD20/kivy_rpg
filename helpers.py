import os
import sys
from collections import defaultdict
from functools import wraps
from os.path import exists

from kivy.app import App
from kivy.uix.image import Image

from widgets.kivy_fix import SpriteAtlas
from kivy.core.window import Window

keys = defaultdict(lambda: False)
runpath = os.path.dirname(os.path.realpath(sys.argv[0]))
os.chdir(runpath)  # I added this during testing on android, but I doubt it's needed now.
print(runpath)
images = SpriteAtlas('images/tiles.atlas')
app = App()  # this is ugly, but I needed to use it to get app.user_data_dir before the actual app starts...

data_dir = app.user_data_dir
if not exists(data_dir):
    os.mkdir(data_dir)  # If the directory doesn't exist, create it before returning the path
print('Data Directory: {}'.format(data_dir))

SAVE_PATH = os.path.join(data_dir, 'kivy_rpg_saves/')
if not exists(SAVE_PATH):
    os.mkdir(SAVE_PATH)  # If the directory doesn't exist, create it before returning the path
print('Save Directory: {}'.format(SAVE_PATH))

SCRIPT_PATH = os.path.join(os.path.curdir, 'scripts/')
MAP_PATH = os.path.join(os.path.dirname(__file__), 'maps/')
if not exists(MAP_PATH):
    os.mkdir(MAP_PATH)  # If the directory doesn't exist, create it before returning the path
print('Map Directory: {}'.format(MAP_PATH))

screen_width, screen_height = Window.size
print('size', Window.size)


def memoized(f):
    """Decorator that caches a function's return value each time it is
    called. If called later with the same arguments, the cached value
    is returned, and not re-evaluated.  This is fine to use for this
    scenario, because if a result was recorded, the work has been
    done already.  It achieves the purpose, even if we don't use
    the cached result.
    """
    cache = {}

    @wraps(f)
    def wrapped(*args):
        try:
            result = cache[args]
        except KeyError:
            result = cache[args] = f(*args)
        return result
    return wrapped


class Sprite(Image):
    pass

