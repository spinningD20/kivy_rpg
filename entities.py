import os

from cymunk.cymunk import Body, Vec2d, Poly
from kivy.graphics.context_instructions import Color
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

from events import EventSet
from helpers import Sprite, SCRIPT_PATH
from states.turn import WaitingForTurn, State
from states.realtime import EntityIdle
from xml.etree import ElementTree


class FogOfWarCell(Widget):
    color = ObjectProperty()


class CellPoly(Poly):
    def __init__(self, c):
        vertices = [Vec2d(0, 0), Vec2d(0, c.px_height), Vec2d(c.px_width, c.px_height), Vec2d(c.px_width, 0)]
        body = Body(1, 1)
        body.position = c.bottomleft
        super(CellPoly, self).__init__(body, vertices)
        self.cell = c
        self.color = Color(rgba=[0, 0, 0, 1])


class EntityPoly(Poly):
    def __init__(self, entity, game, body, vertices, offset=(0, 0), radius=0):
        super(EntityPoly, self).__init__(body, vertices, offset, radius)
        self.entity = entity
        # self.space = game.space


class StaticEntity(Widget):
    def __init__(self, data, game, map, **kwargs):
        print('static', kwargs)
        super(StaticEntity, self).__init__()
        self.data = data
        print('static entity data looks like', self.data.properties, self.data.id)
        self.xml = ElementTree.parse(os.path.join('scripts/', self.data.properties['action_xml'])).getroot()
        self.x, self.y = data.x, data.y
        self.game = game
        self.map = map
        ts = map.tile_width
        padding = 5
        self.body = Body(1, 1)
        self.body.position = self.x, self.y
        print('about to add static entity shape')
        self.shape = EntityPoly(self, game, self.body,
                                [Vec2d(padding, padding), Vec2d(padding, ts-padding),
                               Vec2d(ts-padding, ts-padding), Vec2d(ts-padding, padding)])
        self.shape.sensor = True
        self.shape.collision_type = 19


class Entity(Sprite):
    def __init__(self, data, game, map, sprite_name='clyde', **kwargs):
        self.data = data
        self.incapacitated = False
        self.game = game
        self.map = map
        pos = data.x + self.map.tile_width, data.y + self.map.tile_width
        super(Entity, self).__init__(pos=pos)

        self._current_cell = self.map.layers['below'].get_at(*self.center)
        # if self._current_cell is not None:
        #     self._current_cell.occupied = True
        self.turn_points = 100
        self.sprite_name = sprite_name
        self.facing = 'down'
        ts = self.map.tile_width
        self.size = (ts, ts)
        self.body = Body(1, 1)
        self.body.position = self.center
        d_range = ts * 4
        topleft = Vec2d(-d_range, d_range)
        topright = Vec2d(d_range, d_range)
        bottomleft = Vec2d(-d_range, -d_range)
        bottomright = Vec2d(d_range, -d_range)
        center = Vec2d(0, 0)
        self.detector_position = {
            'left': 4.71239,
            'right': 1.5708,
            'up': 3.14159,
            'down': 0
        }

        self.detector = EntityPoly(self, game, self.body, [center, bottomright, bottomleft])
        padding = 5
        self.shape = EntityPoly(self, game, self.body,
                                [Vec2d(-(ts/2)+padding, -(ts/2)+padding), Vec2d(-(ts/2)+padding, (ts/2)-padding),
                               Vec2d((ts/2)-padding, (ts/2)-padding), Vec2d((ts/2)-padding, -(ts/2)+padding)])
        self.shape.collision_type = 1  # E for entity
        self.detector.collision_type = 100
        # self.shape.sensor = True
        self.detector.sensor = True
        self.set_face(self.facing)
        self.anim_delay = -1
        self.state = WaitingForTurn(self)

    def set_face(self, direction):
            self.facing = direction
            self.source = 'images/sprites/' + self.sprite_name + '_' + direction + '.zip'
            self.body.angle = self.detector_position[direction]

    def get_current_cell(self):
        cell = self.map.layers['below'].get_at(*self.center)
        # self._current_cell.occupied = False
        # cell.occupied = True
        self._current_cell = cell
        return cell

    def set_position(self, x, y):
        # print('set position called')
        self.x, self.y = x, y
        self.body.position = self.center
        self.data.x, self.data.y = x, y

    def on_complete(self, *args):
        pass

    def on_start(self, *args):
        pass

    def update(self, dt):
        if not self.state.ended:
            self.state.update(dt)

    def move_range(self):
        return self.turn_points / 25  # move_cost

    def spend_moves(self, moves):
        print('cost was', 15 * moves)  # self.move_cost
        self.turn_points -= 15 * moves  # self.move_cost

    def start_battle(self):
        print('starting battle')
        self.state.end()
        self.state = WaitingForTurn(self)

    def exit_battle(self):
        print('exiting battle')
        self.state.end()
        self.state = WaitingForTurn(self)


class Player(Entity):
    def __init__(self, data, game, map, sprite_name='clyde', **kwargs):
        self.data = data
        self.incapacitated = False
        self.game = game
        self.map = map
        self.state = State(self)
        pos = data.x + self.map.tile_width, data.y + self.map.tile_width
        super(Sprite, self).__init__(pos=pos)

        self._current_cell = self.map.layers['below'].get_at(*self.center)
        # if self._current_cell is not None:
        #     self._current_cell.occupied = True
        self.turn_points = 100
        self.sprite_name = sprite_name
        self.facing = 'down'
        self.body = Body(1, 1)
        self.body.position = self.x, self.y

        self.objects = []  #  this is to keep track of things that the detector has highlighted - should only be one
        self.collidables = []  # same as above but this is floor / underneath / triggered without button press
        ts = self.map.tile_width
        d_range = self.map.tile_width * 4.5
        center = Vec2d(0, 0)
        self.size = (ts, ts)
        self.body = Body(1, 1)
        self.body.position = self.x, self.y
        padding = 5
        self.shape = EntityPoly(self, game, self.body,
                                [Vec2d(-(ts/2)+padding, -(ts/2)+padding), Vec2d(-(ts/2)+padding, (ts/2)-padding),
                               Vec2d((ts/2)-padding, (ts/2)-padding), Vec2d((ts/2)-padding, -(ts/2)+padding)])
        self.interactor = EntityPoly(self, self.game, self.body, [center, Vec2d(ts/2.25, -ts), Vec2d(-ts/2.25, -ts)])
        self.interactor.collision_type = 116
        self.interactor.sensor = True
        self.detector_position = {
            'left': 4.71239,
            'right': 1.5708,
            'up': 3.14159,
            'down': 0
        }
        self.detector = EntityPoly(self, self.game, self.body, [center, Vec2d(d_range, -d_range), Vec2d(-d_range, -d_range)])
        self.detector.collision_type = 216
        self.detector.sensor = True
        self.data.properties['current_speed'] = 15
        self.shape.collision_type = 16
        self.set_face(self.facing)
        self.allow_stretch = True
        self.anim_delay = -1

    def activate_object(self, target='interactive', button_press=True):
        if self.game:
            # print('activating', self.collidables, target)
            if self.objects and target == 'interactive':
                entity = self.objects[0]
            elif self.collidables:  # assume not interactive
                print('collidables and target is floor')
                entity = self.collidables[0]
            else:
                return
            for set_xml in sorted(entity.xml.findall('action_set'), key=lambda s: s.attrib['order']):
                if set_xml.attrib['flag_required'] in self.game.player_flags:
                    # check the event set's interaction type.  So far this is just to separate explicit button press
                    interaction_type = set_xml.attrib.get('interaction')
                    # if it's not specified or interaction is button type, then button event is True
                    button_event = (not interaction_type) or (interaction_type.lower() == 'button_press')
                    if (button_press and button_event) or (not button_press and not button_event):
                        self.game.set_event(EventSet(set_xml, self.game))
                        if self.game and self.game.event_in_progress.pausing:
                            self.anim_delay = -1
                        break

    def set_face(self, direction):
            self.facing = direction
            self.source = 'images/sprites/' + self.sprite_name + '_' + direction + '.zip'
            self.body.angle = self.detector_position[direction]

    def start_battle(self):
        print('starting battle')
        self.state.end()
        self.state = WaitingForTurn(self)

    def exit_battle(self):
        print('exiting battle')
        if self.state is not None:
            self.state.end()
        self.state = WaitingForTurn(self)


class Enemy(Entity):
    def __init__(self, *args, **kwargs):
        super(Enemy, self).__init__(*args, **kwargs)
        self.shape.collision_type = 3
        self.detector.collision_type = 105
        self.data.properties['current_speed'] = 8

    def start_battle(self):
        self.state.end()
        self.state = WaitingForTurn(self)

    def exit_battle(self):
        self.state.end()
        self.state = EntityIdle(self)


class NPC(Entity):
    def __init__(self, *args, **kwargs):
        super(NPC, self).__init__(*args, **kwargs)
        self.xml = ElementTree.parse(SCRIPT_PATH + self.data.properties['action_xml']).getroot()
        self.shape.collision_type = 14
        self.detector.collision_type = 114
        print('loaded xml', self.xml)

    def start_battle(self):
        self.state.end()
        self.state = WaitingForTurn(self)

    def exit_battle(self):
        self.state.end()
        self.state = EntityIdle(self)


class FloorEntity(StaticEntity):
    def __init__(self, data, game, map, **kwargs):
        super(FloorEntity, self).__init__(data, game, map, **kwargs)
        self.shape.collision_type = 6