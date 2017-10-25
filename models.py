import base64
import os

import zlib
from kivy.app import App
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from genericpath import exists
import sys
import struct
from xml.etree import ElementTree

from rect import Rect

from kivy.uix.image import Image
from sqlalchemy.types import PickleType
import heapq
from sqlalchemy.orm.session import object_session

Base = declarative_base()
MAP_PATH = os.path.join(os.path.dirname(__file__), 'maps/')
if not exists(MAP_PATH):
    os.mkdir(MAP_PATH)  # If the directory doesn't exist, create it before returning the path


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)
            return Mutable.coerce(key, value)
        else:
            return value

    def __delitem(self, key):
        dict.__delitem__(self, key)
        self.changed()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(self)


class Model(Base):
    """Base model class that includes CRUD convenience methods."""
    __abstract__ = True

    @classmethod
    def create(cls, **kwargs):
        """Create a new record and save it the database."""
        # print(kwargs)
        instance = cls(**kwargs)
        return instance.save()

    def update(self, commit=True, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        """Save the record."""
        db = object_session(self)
        db.add(self)
        if commit:
            db.commit()
        return self

    def delete(self, commit=True, *args, **kwargs):
        """Remove the record from the database."""
        db = object_session(self)
        db.add(self)
        db.delete(self)
        return commit and db.commit()

    @property
    def data(self):
        dict_ = {}
        for key in self.__mapper__.c.keys():
            dict_[key] = getattr(self, key)
        return dict_


class Item(Model):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    type = Column(String(64))
    image = Column(String(64))
    category = Column(Integer)
    identification_level = Column(Integer)
    internal_value = Column(Integer)
    required_equip = Column(Integer)


class GameFlag(Model):
    __tablename__ = 'game_flags'
    name = Column(String(64), primary_key=True)
    value = Column(String(64))


class TileMap(Model):
    # switch the tilemap xml loading to have that data in db sometime in future.  For now, read from tmx files.
    __tablename__ = 'maps'
    id = Column(Integer, primary_key=True)
    file_name = Column(String(32))
    full_name = Column(String(64))
    height = Column(Integer)
    width = Column(Integer)
    fog_of_war = Column(MutableDict.as_mutable(PickleType))
    objects = relationship('MapObject')

    def resize_view(self, x, y):
        self.view_w = x
        self.view_h = y

    def recenter(self, w, h):
        self.view_w, self.view_h = (w, h)  # viewport size
        self.viewport = Rect(*(self.view_x, self.view_y) + (self.view_w, self.view_h))

    def load(self, viewport_size=(100, 100), viewport_origin=(0, 0)):
        print('loading tilemap db object now')
        filename = 'maps/{}'.format(self.file_name)
        self.properties = {}
        self.layers = Layers()
        self.tilesets = Tilesets()
        self.fx, self.fy = 0, 0  # viewport focus point
        self.view_w, self.view_h = viewport_size  # viewport size
        self.view_x, self.view_y = viewport_origin  # viewport offset
        self.viewport = Rect(*(viewport_origin + viewport_size))

        with open(filename) as f:
            xml = ElementTree.fromstring(f.read())
        print('xml found')
        # get most general map information and create a surface
        self.tile_width = int(xml.attrib['tilewidth'])
        self.tile_height = int(xml.attrib['tileheight'])
        self.px_width = self.width * self.tile_width
        self.px_height = self.height * self.tile_height
        self.file_path = os.path.dirname(filename)

        for tag in xml.findall('tileset'):
            self.tilesets.add(Tileset.fromxml(tag, self))
        print('tilesets loaded', self.tilesets)
        for tag in xml.findall('layer'):
            layer = Layer.fromxml(tag, self)
            self.layers.add_named(layer, layer.name)
        print('layers loaded', self.layers)
        if not self.fog_of_war:
            self.generate_fog()
            self.save()

    def save(self, commit=True):
        # fog_of_war = self.fog_of_war
        # self.fog_of_war = None
        # self.fog_of_war = fog_of_war
        super(TileMap, self).save(commit)

    def generate_fog(self):
        self.fog_of_war = dict()
        for c in self.layers.by_name['below'].cells:
            self.fog_of_war.update({c: True})

    def update(self, dt, *args):
        for layer in self.layers:
            layer.update(dt, *args)

    _old_focus = None

    def force_focus(self, fx, fy):
        """Force the manager to focus on a point, regardless of any managed layer
        visible boundaries.
        """
        self.fx, self.fy = fx, fy

        # get our view size
        w = self.view_w
        h = self.view_h
        w2, h2 = w // 2, h // 2

        # bottom-left corner of the viewport
        x, y = fx - w2, fy - h2
        self.viewport.x = x
        self.viewport.y = y

        self.childs_ox = x - self.view_x
        self.childs_oy = y - self.view_y

        self.set_view(x, y, w, h)

    def set_view(self, x, y, w, h):
        # for layer in self.layers:
        #     print(layer.name)
        self.layers.by_name['below'].set_view(x, y, w, h, self.view_x, self.view_y)

    def pixel_from_screen(self, x, y):
        """Look up the Layer-space pixel matching the screen-space pixel.
        """
        vx, vy = self.childs_ox, self.childs_oy
        return int(vx + x), int(vy + y)

    def pixel_to_screen(self, x, y):
        """Look up the screen-space pixel matching the Layer-space pixel.
        """
        screen_x = x - self.childs_ox
        screen_y = y - self.childs_oy
        return int(screen_x), int(screen_y)

    def index_at(self, x, y):
        """Return the map index at the (screen-space) pixel position.
        """
        sx, sy = self.pixel_from_screen(x, y)
        return int(sx // self.tile_width), int(sy // self.tile_height)

    def save_data(self):
        for map_object in self.objects: # probably turn this into a save method instead?
            map_object.save()
            for object_property in map_object.properties:
                self.db.add(object_property)
        self.db.commit()


class MapObject(Model):
    __tablename__ = 'mapobjects'
    id = Column(Integer, primary_key=True)
    map_id = Column(Integer, ForeignKey('maps.id'))
    name = Column(String(64))
    type = Column(String(32))
    x = Column(Integer)
    y = Column(Integer)
    height = Column(Integer)
    width = Column(Integer)
    object_properties = relationship('MapObjectProperty')
    map = relationship('TileMap')

    @property
    def properties(self):
        dict_ = {}
        for prop in self.object_properties:
            dict_[prop.property] = prop.value
        return dict_

    def __repr__(self):
        return '<Object %s,%s %s,%s>' % (self.x, self.y, self.width, self.height)

    @classmethod
    def query(cls, **kwargs):
        query = App.get_running_app().db.query(cls)
        if 'type' in kwargs:
            query.filter(cls.type == kwargs['type'])
        return query.all()


class MapObjectProperty(Model):
    __tablename__ = 'mapobjectproperties'
    id = Column(Integer, primary_key=True)
    object_id = Column(Integer, ForeignKey('mapobjects.id'))
    property = Column(String(64))
    value = Column(String(1024)) #make this whatever the dialogue display's max for one panel is, probably less than 1024


class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        # priority is only living on the object to work around python3 comparison logic
        item.priority = priority
        heapq.heappush(self.elements, item)

    def get(self):
        return heapq.heappop(self.elements)


class GridWithWeights(object):
    def __init__(self, layer):
        self.layer = layer
        self.weights = {}

    def cost(self, from_node, to_node):
        return self.weights.get(to_node, 1)


def heuristic(a, b):
    (x1, y1) = a.x, a.y
    (x2, y2) = b.x, b.y
    return abs(x1 - x2) + abs(y1 - y2)


def reconstruct_path(came_from, start, goal):
    current = goal
    path = [current]
    # print(came_from, start, goal)
    while current != start:
        current = came_from[current]
        # print('iteration')
        path.append(current)
    path.reverse()
    return path


class Tile(object):

    def __init__(self, gid, texture, tileset):
        self.gid = gid
        self.texture = texture
        self.tile_width = tileset.tile_width
        self.tile_height = tileset.tile_height
        self.properties = {}

    def is_passable(self):
        return True if 'wall' not in self.properties and 'water' not in self.properties else False

    def loadxml(self, tag):
        props = tag.find('properties')
        if props is None:
            return
        for c in props.findall('property'):
            # store additional properties.
            name = c.attrib['name']
            value = c.attrib['value']

            # TODO hax
            if value.isdigit():
                value = int(value)
            self.properties[name] = value

    def __repr__(self):
        return '<Tile %d>' % self.gid


class Tileset(object):

    def __init__(self, name, tile_width, tile_height, firstgid, spacing=0, margin=0):
        self.name = name
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.firstgid = firstgid
        self.spacing = spacing
        self.margin = margin
        self.tiles = []
        self.properties = {}

    @classmethod
    def fromxml(cls, tag, tilemap, firstgid=None):
        if 'source' in tag.attrib:
            firstgid = int(tag.attrib['firstgid'])
            path = tag.attrib['source']
            if not os.path.exists(path):
                path = os.path.join(tilemap.file_path, path)
            with open(path) as f:
                tileset = ElementTree.fromstring(f.read())
            return cls.fromxml(tileset, firstgid)

        name = tag.attrib['name']
        if firstgid is None:
            firstgid = int(tag.attrib['firstgid'])
        tile_width = int(tag.attrib['tilewidth'])
        tile_height = int(tag.attrib['tileheight'])
        spacing = int(tag.get('spacing', 0))
        margin = int(tag.get('margin', 0))

        tileset = cls(name, tile_width, tile_height, firstgid,
                      spacing, margin)

        for c in tag.getchildren():
            if c.tag == "image":
                # create a tileset
                tileset.add_image(tilemap.file_path, c.attrib['source'])
            elif c.tag == 'tile':
                gid = tileset.firstgid + int(c.attrib['id'])
                tileset.get_tile(gid).loadxml(c)
        return tileset

    def add_image(self, base_path, file):
        if not os.path.exists(file):
            file = os.path.join(base_path, file)
        texture = Image(source=file).texture
        print('loading', file)
        texture.mag_filter = 'nearest'
        if texture is None:
            sys.exit('failed to locate image file %r' % file)

        id = self.firstgid
        th = self.tile_height + self.spacing
        tw = self.tile_width + self.spacing
        for j in range(texture.height // th):
            for i in range(texture.width // tw):
                x = (i * tw) + self.margin
                # convert the y coordinate to OpenGL (0 at bottom of texture)
                y = texture.height - ((j + 1) * th)
                tile = texture.get_region(x, y, self.tile_width, self.tile_height)
                self.tiles.append(Tile(id, tile, self))
                id += 1

    def get_tile(self, gid):
        return self.tiles[gid - self.firstgid]


class Tilesets(dict):
    def add(self, tileset):
        for i, tile in enumerate(tileset.tiles):
            i += tileset.firstgid
            self[i] = tile


class Cell(object):
    """Layers are made of Cells (or empty space).


    Cells have some basic properties:

    x, y - the cell's index in the layer
    px, py - the cell's pixel position
    left, right, top, bottom - the cell's pixel boundaries

    Additionally the cell may have other properties which are accessed using
    standard dictionary methods:

       cell['property name']

    You may assign a new value for a property to or even delete an existing
    property from the cell - this will not affect the Tile or any other Cells
    using the Cell's Tile.
    """

    def __init__(self, layer, x, y, px, py, tile):
        self.layer = layer
        self.occupied = False
        self.map_px = px
        self.map_py = py
        self.x, self.y = x, y
        self.px, self.py = px, py
        self.px_width, self.px_height = tile.tile_width, tile.tile_height
        self.py = layer.px_height - py - tile.tile_height # corrected y positioning, I don't get why yet though...
        self.size = self.px_width, self.px_height
        self.tile = tile
        self.bottomleft = (px, py)
        self.left = px
        self.right = px + self.px_width
        self.bottom = py
        self.top = py + self.px_height
        self.center = (px + self.px_width // 2, py + self.px_height // 2)
        self._added_properties = {}
        self._deleted_properties = set()
        self.priority = 0

    # this is here only for python3 comparison for heapq push
    def __lt__(self, other):
        return self.priority < other.priority

    def __repr__(self):
        return '<Cell at %s %s>' % (self.x, self.y)

    def __contains__(self, key):
        if key in self._deleted_properties:
            return False
        return key in self._added_properties or key in self.tile.properties

    def __getitem__(self, key):
        if key in self._deleted_properties:
            raise KeyError(key)
        if key in self._added_properties:
            return self._added_properties[key]
        if key in self.tile.properties:
            return self.tile.properties[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        self._added_properties[key] = value

    def __delitem__(self, key):
        self._deleted_properties.add(key)

    def intersects(self, other):
        """
        Determine whether this Cell intersects with the other rect (which has
        .x, .y, .width and .height attributes.)
        """
        if self.px + self.px_width < other.x:
            return False
        if other.x + other.width < self.px:
            return False
        if self.py + self.px_height < other.y:
            return False
        if other.y + other.height < self.py:
            return False
        return True


class LayerIterator(object):
    """Iterates over all the cells in a layer in column,row order.
    """

    def __init__(self, layer):
        self.layer = layer
        self.i, self.j = 0, 0

    def __next__(self):
        if self.i == self.layer.width:
            self.j += 1
            self.i = 0
        if self.j == self.layer.height:
            raise StopIteration()
        value = self.layer[self.i, self.j]
        self.i += 1
        return value

    def next(self):
        if self.i == self.layer.width:
            self.j += 1
            self.i = 0
        if self.j == self.layer.height:
            raise StopIteration()
        value = self.layer[self.i, self.j]
        self.i += 1
        return value


class Layer(object):
    """A 2d grid of Cells.

    Layers have some basic properties:

        width, height - the dimensions of the Layer in cells
        tile_width, tile_height - the dimensions of each cell
        px_width, px_height - the dimensions of the Layer in pixels
        tilesets - the tilesets used in this Layer (a Tilesets instance)
        properties - any properties set for this Layer
        cells - a dict of all the Cell instances for this Layer, keyed off
                (x, y) index.

    Additionally you may look up a cell using direct item access:

       layer[x, y] is layer.cells[x, y]

    Note that empty cells will be set to None instead of a Cell instance.
    """

    def __init__(self, name, visible, map):
        self.name = name
        self.visible = visible
        self.position = (0, 0)
        self.px_width = int(map.px_width)
        self.px_height = int(map.px_height)
        self.tile_width = int(map.tile_width)
        self.tile_height = int(map.tile_height)
        self.width = int(map.width)
        self.height = int(map.height)
        self.tilesets = map.tilesets
        self.properties = {}
        self.cells = {}
        self.all_cells = []
        self.walls = []

    def __repr__(self):
        return '<Layer "%s" at 0x%x>' % (self.name, id(self))

    def __getitem__(self, pos):
        return self.cells.get(pos)

    def __setitem__(self, pos, tile):
        x, y = pos
        px = x * self.tile_width
        py = y * self.tile_width
        rev_y = self.px_height - py - self.tile_height // self.tile_height
        cell = Cell(self, x, y, px, py, tile)
        self.cells[(x, rev_y)] = cell
        self.all_cells.append(cell)
        if 'wall' in tile.properties:
            self.walls.append(cell)

    def __iter__(self):
        return LayerIterator(self)

    @classmethod
    def fromxml(cls, tag, map):
        # print(type(map))
        layer = cls(tag.attrib['name'], int(tag.attrib.get('visible', 1)), map)

        data = tag.find('data')
        # print(ElementTree.tostring(data))
        if data is None:
            raise ValueError('layer %s does not contain <data>' % layer.name)
        # print('layer data not none')
        data = data.text.strip()
        data = zlib.decompress(base64.b64decode(data))
        data = struct.unpack('<%di' % (len(data) / 4,), data)
        assert len(data) == layer.width * layer.height, "data len (%d) != width (%d) x height (%d)" % (
        len(data), layer.width, layer.height)
        for i, gid in enumerate(data):
            if gid < 1: continue  # not set
            tile = map.tilesets[gid]
            x = i % layer.width
            y = i // layer.width
            layer.cells[x, y] = Cell(layer, x, y, x * layer.tile_width, y * layer.tile_height, tile)
        # print(layer.name, 'cells are now', layer.cells)
        return layer

    def update(self, dt, *args):
        pass

    def set_view(self, x, y, w, h, viewport_ox=0, viewport_oy=0):
        self.view_x, self.view_y = x, y
        self.view_w, self.view_h = w, h
        x -= viewport_ox
        y -= viewport_oy
        self.position = (x, y)

    def find(self, *properties):
        """Find all cells with the given properties set.
        """
        r = []
        for propname in properties:
            for cell in self.cells.values():
                if cell and propname in cell:
                    r.append(cell)
        return r

    def match(self, **properties):
        """Find all cells with the given properties set to the given values.
        """
        r = []
        for propname in properties:
            for cell in self.cells.values():
                if propname not in cell:
                    continue
                if properties[propname] == cell[propname]:
                    r.append(cell)
        return r

    def collide(self, rect, propname):
        """Find all cells the rect is touching that have the indicated property
        name set.
        """
        r = []
        for cell in self.get_in_region(rect.left, rect.bottom, rect.right,
                                       rect.top):
            if not cell.intersects(rect):
                continue
            if propname in cell:
                r.append(cell)
        return r

    def get_in_region(self, x1, y1, x2, y2):
        """Return cells (in [column][row]) that are within the map-space
        pixel bounds specified by the bottom-left (x1, y1) and top-right
        (x2, y2) corners.

        Return a list of Cell instances.
        """
        i1 = max(0, x1 // self.tile_width)
        j1 = max(0, y1 // self.tile_height)
        i2 = min(self.width, x2 // self.tile_width + 1)
        j2 = min(self.height, y2 // self.tile_height + 1)
        return [self.cells[i, j]
                for i in range(int(i1), int(i2))
                for j in range(int(j1), int(j2))
                if (i, j) in self.cells]

    def get_tile(self, tx, ty):
        return self.cells.get((tx, ty))

    def get_at(self, x, y, y_offset=1, reverse_y=True):
        # print('get at called')
        """Return the cell at the nominated (x, y) coordinate.

        Return a Cell instance or None.
        """
        i = x // self.tile_width
        j = y // self.tile_height + y_offset
        j = (self.height - j) if reverse_y else j
        return self.cells.get((i, j))

    def passable(self, cell):
        return cell.tile.is_passable()

    def in_bounds(self, cell):
        return self.cells.get((cell.x, cell.y)) is not None

    def occupied(self, cell):
        return not cell.occupied

    def get_neighbor_cells(self, cell):
        # print(self.neighbors((cell.x, cell.y)))
        if cell:
            cells = [self.cells.get(n) for n in self.neighbors((cell.x, cell.y))]
            # print('cells before filter', cells)
            cells = filter(self.in_bounds, cells)
            # print('cells after is passable', cells)
            cells = filter(self.passable, cells)
            # cells = filter(self.occupied, cells) I think this logic needs to be at the usage level, after results given

            return cells
        return []

    def a_star_search(self, start, goal):
        graph = GridWithWeights(self)
        frontier = PriorityQueue()
        frontier.put(start, 0)
        came_from = dict()
        cost_so_far = dict()
        came_from[start] = None
        cost_so_far[start] = 0

        while not frontier.empty():
            cell = frontier.get()

            if cell == goal:
                # print('cell is goal', start, goal)
                break

            for next_cell in self.get_neighbor_cells(cell):
                new_cost = cost_so_far[cell] + graph.cost(cell, next_cell)
                if next_cell not in cost_so_far or new_cost < cost_so_far[next_cell]:
                    cost_so_far[next_cell] = new_cost
                    priority = new_cost + heuristic(goal, next_cell)
                    frontier.put(next_cell, priority)
                    came_from[next_cell] = cell
        if goal not in came_from:
            print('could not reach goal based on get neighbor cell results', start, goal)
            return [start, goal]

        return reconstruct_path(came_from, start, goal)

    def neighbors(self, index):
        """Return the indexes of the valid (ie. within the map) cardinal (ie.
        North, South, East, West) neighbors of the nominated cell index.

        Returns a list of 2-tuple indexes.
        """
        i, j = index
        n = []
        if i < self.width - 1:
            n.append((i + 1, j))
        if i > 0:
            n.append((i - 1, j))
        if j < self.height - 1:
            n.append((i, j + 1))
        if j > 0:
            n.append((i, j - 1))
        return n


class SpriteLayer(object):
    def __init__(self):
        super(SpriteLayer, self).__init__()
        self.visible = True

    def set_view(self, x, y, w, h, viewport_ox=0, viewport_oy=0):
        self.view_x, self.view_y = x, y
        self.view_w, self.view_h = w, h
        x -= viewport_ox
        y -= viewport_oy
        self.position = (x, y)


class Layers(list):
    def __init__(self):
        self.by_name = {}

    def add_named(self, layer, name):
        self.append(layer)
        self.by_name[name] = layer

    def __getitem__(self, item):
        # print('getting layers by name', self.by_name)
        if isinstance(item, int):
            return self[item]
        return self.by_name[item]


def load(filename, viewport):
    return TileMap.load(filename, viewport)


# frequently used in almost all game states.
# class Skill(Model):
#     id = Column(Integer, ForeignKey('characters.id'))
#     character_id = Column
#     name = Column
#     base = Column
#     value = Column
#
#
# class SkillSet(object):
#     def __init__(self, character):
#         for skill in character.skills:
#             setattr(self, skill.name, skill)
#
#
# # come back to this one... does this just belong on the character model?
# # this would maybe be used for displaying the character sprite/paper doll with equipment, otherwise only during battle equations
# class EquipmentSet(object):
#     head = None
#     neck = None
#     shoulders = None
#     arms = None
#     left_hand = None
#     right_hand = None
#     torso = None
#     waist = None
#     legs = None
#     feet = None
#
#     def __init__(self, container):
#         for item in container:
#             item_type = item.type
#             setattr(self, item_type, item)
#
#
# class Character(Model):
#     __tablename__ = 'characters'
#     id = Column(Integer, primary_key=True)
#     map_id = Column(Integer, ForeignKey('maps.id'))
#     name = Column
#     race = Column(String(16))
#     gender = Column(String(8))
#     soul_state = Column(String(8))
#     soul_type = Column(String(16))
#     inventory_id = Column(Integer, ForeignKey('containers.id'))
#     inventory = relationship('Container', foreign_keys='Character.inventory_id')
#     equipment_set_id = Column(Integer, ForeignKey('containers.id'))
#     equipment_set = relationship('Container', foreign_keys='Character.inventory_id')
#     attributes = relationship('Attribute')
#     skills = relationship('Skill')
#
#     def construct(self):
#         self.skillset = SkillSet(self)
#
#
#
