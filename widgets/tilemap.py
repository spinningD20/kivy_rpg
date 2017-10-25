import os

from cymunk.cymunk import Space
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.context_instructions import PushMatrix, Translate, PopMatrix
from os.path import exists

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.scatter import Scatter

from entities import FloorEntity, Enemy, NPC, Player
from helpers import MAP_PATH
from models import MapObject
from rect import Rect
from states.realtime import IdleReadyState, EntityFollow
from states.turn import BattleMenuState, WaitingForTurn


class MapLayer(Image):

    def __init__(self, **kwargs):
        super(MapLayer, self).__init__(**kwargs)
        if self.texture:
            self.texture.mag_filter = 'nearest'
            self.texture.min_filter = 'nearest'


class MapScalar(Scatter):

    # we don't want to allow dragging things around!
    def on_touch_move(self, touch):
        return True


class TileMapWidget(FloatLayout):
    def __init__(self, tilemap, **kwargs):
        super(TileMapWidget, self).__init__(**kwargs)
        self.jobs = []
        self.space = Space()
        self.space.gravity = (0.0, 0.0)
        self.objects = []
        self.in_battle = False
        self.entities = []
        self.player_characters = []
        self.player_flags = ['testing']  # eventually this will be in DB for progress_flags
        self.enemy_characters = []
        self.event_in_progress = None
        self.last_focus = None
        self.current_battler = None
        self.current_character = None
        self.battle_entities = list()
        self.spent_battlers = set()
        self.focus_target = None
        self.map = tilemap
        tilemap.load(Window.size)
        self.size = (float(self.map.px_width), float(self.map.px_height))
        self.layer_widgets = {}

        # for layer in self.map.layers:
        #     layer_widget = Widget()
        #     with layer_widget.canvas:
        #         if hasattr(layer, 'color') and layer.color:
        #             c = get_color_from_hex(layer.color)
        #             c[-1] = .2
        #             Color(*c)
        #         else:
        #             Color(1, 1, 1, 1)
        #         if not layer.visible:
        #             continue
        #         for cell in layer:
        #             if cell is None:
        #                 continue
        #             x = cell.px
        #             # OpenGL vs. TMX, y is reversed
        #             y = cell.py
        #             # Rectangle(pos=(x, y), size=[32, 32])
        #             # Color(rgba=[1, 0, 0, .5])
        #             if cell.tile:
        #                 texture = cell.tile.texture
        #                 size = cell.px_width, cell.px_height
        #                 Rectangle(pos=(x, y), texture=texture, size=size, allow_stretch=True)
        #             else:
        #                 Rectangle(pos=(cell.px, cell.py), size=(cell.width, cell.height))
        #     self.add_widget(layer_widget)
        #     self.layer_widgets.update({layer.name: layer_widget})

        for layer in self.map.layers:
            image = os.path.join(MAP_PATH, str(self.map.file_name).split('.')[0] + '_' + layer.name + '.png')
            print('Layer Image File at?', image)
            layer_widget = MapLayer(source=image)

            if exists(image):
                self.add_widget(layer_widget)
            self.layer_widgets.update({layer.name: layer_widget})

        # for c in self.map.fog_of_war:
        #     # print('cell', c)
        #     cell = self.map.layers.by_name['below'].cells[c]
        #     shape = CellPoly(cell)
        #     shape.sensor, shape.collision_type = True, 1020
        #     self.space.add(shape)
        #     self.canvas.add(Rectangle(pos=(cell.px, cell.py), size=(cell.px_width, cell.px_width)))
        #     self.canvas.add(shape.color)
        #     # just being more explicit with this condition, because data existing equates to True too.
        #     if self.map.fog_of_war[c] != True:
        #         # print('not true!', c)
        #         shape.color.rgba = [0, 0, 0, .2]

        primary = None
        for floor_data in App.get_running_app().db.query(MapObject).filter(MapObject.map_id == self.map.id, MapObject.type == 'floor_entity').all():
            entity_widget = FloorEntity(floor_data, self, self.map, **floor_data.properties)
            self.space.add(entity_widget.body, entity_widget.shape)

        for enemy_data in App.get_running_app().db.query(MapObject).filter(MapObject.map_id == self.map.id, MapObject.type == 'enemy').all():
            entity_widget = Enemy(enemy_data, self, self.map, **enemy_data.properties)
            self.entities.append(entity_widget)
            self.enemy_characters.append(entity_widget)

        for npc_data in App.get_running_app().db.query(MapObject).filter(MapObject.map_id == self.map.id, MapObject.type == 'npc').all():
            entity_widget = NPC(npc_data, self, self.map, **npc_data.properties)
            self.entities.append(entity_widget)

        for player_data in App.get_running_app().db.query(MapObject).filter(MapObject.map_id == self.map.id, MapObject.type == 'player').all():
            entity_widget = Player(player_data, self, self.map, **player_data.properties)
            self.entities.append(entity_widget)
            self.player_characters.append(entity_widget)
            if player_data.properties.get('primary'):
                print('found primary')
                primary = entity_widget

        if primary is not None:
            self.current_character = primary
        elif self.player_characters:
            self.current_character = self.player_characters[0]
        self.focus_target = self.current_character
        self.current_character.state = IdleReadyState(self.current_character)
        print(self.current_character, self.current_character.state)

        for entity in self.entities:
            entity.opacity = 1
            self.space.add(entity.shape, entity.detector)
            self.layer_widgets['sprite_layer'].add_widget(entity)

        for player in self.player_characters:
            player.opacity = 1
            self.space.add(player.interactor)

        print('we have {} entities'.format(len(self.entities)))
        self.layer_widgets['sprite_layer'].bind(on_touch_down=self.handle_touch)
        self.switch_to_real_time_state()
        self.space.add_collision_handler(16, 105, self.aggro_collide, None, None, None)
        # self.space.add_collision_handler(105, 216,
        # lambda s, v: self.set_visible(s, v, True), None, None, lambda s, v: self.set_visible(s, v, False))
        # self.space.add_collision_handler(14, 216,
        # lambda s, v: self.set_visible(s, v, True), None, None, lambda s, v: self.set_visible(s, v, False))
        # self.space.add_collision_handler(216, 1020,
        # lambda s, v: self.clear_fog(s, v), None, None, lambda s, v: self.exit_fog(s, v))
        self.space.add_collision_handler(116, 14, self.add_object, None, None, self.remove_object)
        self.space.add_collision_handler(16, 6, self.add_collidable, None, None, self.remove_collidable)
    #   self.space.set_default_collision_handler(
    # self.default_handler, self.default_handler, self.default_handler, self.default_handler)
    #
    # def default_handler(self, arbiter):
    #     print('default handler', arbiter.shapes)

    def update(self, dt):
        if self.event_in_progress:
            if not self.event_in_progress.pausing:
                self.entity_update(dt)
            self.event_in_progress.update(dt)
        else:
            self.entity_update(dt)

    def entity_update(self, dt):
        for entity in self.entities:
            # print(entity, entity.body.position)
            entity.update(dt)
        # print(self.space.shapes)
        # self.scroll(dt)

    def set_focus_target(self, target):
        self.focus_target = target

    def scroll(self, dt):
        if self.focus_target:
            self.force_focus(*self.focus_target.center)

    def start(self, *args):
        self.jobs.append(Clock.schedule_interval(self.update, 1.0/60.0))
        self.jobs.append(Clock.schedule_interval(self.scroll, 1.0/60.0))
        self.jobs.append(Clock.schedule_interval(self.space.step, 1.0/60.0))
        self.jobs.append(Clock.schedule_interval(self.battle_check, .25))
        # self.jobs.append(Clock.schedule_interval(self.save_data, 10))

    def stop(self):
        for job in self.jobs:
            job.cancel()
        for entity in self.entities:
            entity.game = None
            entity.map = None
            del entity
        del self.map
        del self.space
        self.focus_target = None
        for layer in self.layer_widgets:
            self.remove_widget(self.layer_widgets[layer])
            del layer
        self.parent.remove_widget(self)

    def save_data(self, dt=0):
        print('saving map data')
        # gc.collect()
        self.map.save()

    def clear_fog(self, space, arbiter):
        # print('clearing fog', space, arbiter)
        shape = arbiter.shapes[1]
        shape.color.rgba = [0, 0, 0, 0]
        # Animation(opacity=0, duration=.1).start(shape.widget)
        self.map.fog_of_war[(shape.cell.x, shape.cell.y)] = False
        return False

    def exit_fog(self, space, arbiter):
        # print('exiting fog', space, arbiter)
        # Animation(opacity=.2, duration=.2).start(arbiter.shapes[1].widget)
        arbiter.shapes[1].color = [0, 0, 0, .2]
        return False

    def set_visible(self, space, arbiter, visible):
        print('setting visible', space, arbiter, visible)

        arbiter.shapes[0].entity.opacity = 1 if visible else 0
        return False

    def force_focus(self, x, y):
        self.map.force_focus(x, y)
        self._set_view()

    def _set_view(self):
        fx, fy = self.map.viewport.origin
        # clear any previous before/after instructions
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            PushMatrix('projection_mat')
            Translate(-fx, -fy)
        with self.canvas.after:
            PopMatrix('projection_mat')

    def set_event(self, event):
        self.event_in_progress = event

    def add_object(self, space, arbiter):
        print('adding object', space, arbiter)
        entity = arbiter.shapes[1].entity
        arbiter.shapes[0].entity.objects.append(entity)
        return False

    def remove_object(self, space, arbiter):
        print('removing object', space, arbiter)
        entity = arbiter.shapes[1].entity
        if entity in arbiter.shapes[0].entity.objects:
            arbiter.shapes[0].entity.objects.remove(entity)
        return False

    def add_collidable(self, space, arbiter):
        print('adding collidable', space, arbiter)
        entity = arbiter.shapes[1].entity
        arbiter.shapes[0].entity.collidables.append(entity)
        return False

    def remove_collidable(self, space, arbiter):
        print('removing collidable', space, arbiter)
        entity = arbiter.shapes[1].entity
        if entity in arbiter.shapes[0].entity.collidables:
            arbiter.shapes[0].entity.collidables.remove(entity)
        return False

    def handle_touch(self, widget, touch):
        self.current_character.state.touch(touch)

    def aggro_collide(self, space, arbiter):
        print('aggro_collide', space, arbiter)
        entity = arbiter.shapes[1].entity
        if not self.in_battle:
            if not isinstance(entity.state, EntityFollow):
                entity.state.end()
                entity.state = EntityFollow(entity, arbiter.shapes[0].entity)

        print('collision occurred!', space, arbiter)

    def cycle_character(self, right=True):
        party_total = len(self.player_characters)
        print('party total is', party_total)
        if party_total <= 1:
            pass
        else:
            self.current_character.state = WaitingForTurn(self.current_character)
            index = self.player_characters.index(self.current_character)
            print('index is', index)
            index = index + 1 if index + 1 <= party_total - 1 else 0
            self.current_character = self.player_characters[index]
        self.current_character.state = IdleReadyState(self.current_character)
        self.focus_target = self.current_character

    def battle_check(self, *args):
        if not self.in_battle:
            if self.aggro_check(5):
                self.switch_to_battle_state()

    def aggro_check(self, size):
        aggro_range = self.map.tile_width * size
        offset = (self.map.tile_width * (size / 2))
        collided = []
        for player in self.player_characters:
            rect = Rect(player.x - offset, player.y - offset, aggro_range, aggro_range)
            collided += [e for e in self.entities if rect.intersect(Rect(*e.pos + e.size)) and e.data.type == 'enemy']
        return collided

    def switch_to_real_time_state(self, *args):
        self.in_battle = False
        player_character = None
        for entity in self.entities:
            print(entity, entity.data.properties)
            if entity.data.properties.get('faction') == 'player' and not player_character:
                player_character = entity
            if entity.data.properties.get('primary'):
                player_character = entity
            entity.exit_battle()
        if player_character:
            print('found player')
            player_character.state.end()
            player_character.state = IdleReadyState(player_character)
            self.focus_target = player_character

    def switch_to_battle_state(self, *args):
        print('battle started!')
        self.in_battle = True
        for entity in self.entities:
            entity.start_battle()
        self.get_next_turn_taker()
        # Clock.schedule_once(lambda x: setattr(self, 'state', self.battle_loop), 1)

    def get_next_turn_taker(self):
        if self.in_battle:
            if not self.aggro_check(10):
                self.switch_to_real_time_state()
                return
            if len(self.battle_entities) < 1:
                print('refreshing battler list', self.current_battler)
                self.get_battlers()
                self.get_next_turn_taker()
                return
            self.battle_entities.sort(key=lambda entity: entity.data.properties['current_speed'], reverse=True)
            next_battler = self.battle_entities.pop()
            self.spent_battlers.add(next_battler)
            if next_battler.incapacitated:
                self.get_next_turn_taker()
                return
            self.current_battler = next_battler
            self.current_battler.turn_points = 100
            self.current_battler.state.end()
            self.current_battler.state = BattleMenuState(self.current_battler)
            # self.focus_target = self.current_battler

    def get_battlers(self):
        print('get battlers started', self.battle_entities)
        self.battle_entities = list()
        self.spent_battlers = set()
        for entity in self.entities:
            print('getting battler...')
            self.battle_entities.append(entity)
        print('ended', self.battle_entities)
