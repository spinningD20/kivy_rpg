import os
import json
from os.path import dirname, join

from kivy.atlas import Atlas, Logger
from kivy.core.image import Image as CoreImage


class SpriteAtlas(Atlas):
    def _load(self):
        # must be a name finished by .atlas ?
        filename = self._filename
        assert(filename.endswith('.atlas'))
        filename = filename.replace('/', os.sep)

        Logger.debug('Atlas: Load <%s>' % filename)
        with open(filename, 'r') as fd:
            meta = json.load(fd)

        Logger.debug('Atlas: Need to load %d images' % len(meta))
        d = dirname(filename)
        textures = {}
        for subfilename, ids in meta.items():
            subfilename = join(d, subfilename)
            Logger.debug('Atlas: Load <%s>' % subfilename)

            # load the image
            ci = CoreImage(subfilename)

            # <RJ> this is the fix for pixel art
            ci.texture.mag_filter = 'nearest'

            # for all the uid, load the image, get the region, and put
            # it in our dict.
            for meta_id, meta_coords in ids.items():
                x, y, w, h = meta_coords
                textures[meta_id] = ci.texture.get_region(*meta_coords)

        self.textures = textures
