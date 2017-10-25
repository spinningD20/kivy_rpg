from kivy.app import App
from kivy.core.window import Keyboard, Window
from kivy.graphics.context_instructions import Color
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics.vertex_instructions import Rectangle
from kivy.metrics import dp
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.vector import Vector

from effects import Effect, MeleeDamage
from helpers import Sprite, images, memoized, keys
from states.state import State, move


class TurnAction(State):
    def __init__(self, target, **kwargs):
        super(TurnAction, self).__init__(target, **kwargs)
        self.cost = 1
        self.range = 1
        self.shape = 'omni'  # cross, single line, square, cone?
        self.selection_type = 'single'  # pretty much thinking single, all - don't think there are any other patterns
        self.selection_range = 1
        self.selection_shape = 'single'
        self.selected_targets = list()
        self.targeting = 'enemy'  # self, ally, enemy, neutral, all
        self.cursor = 'cursor'  # self for using self.target as the cursor for the camera to follow, else cursor, or future other
        self.effect = Effect
        self.current_effect = None
        self.effect_queue = list()
        self.confirmed = False

    def update(self, dt):
        if not self.confirmed:
            return  # do normal state logic here and return, so nothing else happens and no checks need made
        if not self.current_effect.finished:
            self.current_effect.update(dt)
        else:
            self.ready_next_effect()

    def confirm(self):
        self.confirmed = True
        for target in self.selected_targets:
            print(target, type(target))
            effect = self.effect(target, on_end=self.ready_next_effect)
            self.effect_queue.append(effect)
            self.ready_next_effect()

    def ready_next_effect(self, *args):
        print('readying next effect...')
        if self.effect_queue:
            self.current_effect = self.effect_queue.pop()
            print('current is now', self.current_effect)
        else:
            self.end()


class WaitingForTurn(State):
    def __init__(self, target, **kwargs):
        super(WaitingForTurn, self).__init__(target, **kwargs)
        self.target.set_face(self.target.facing)
        self.target.reload()
        self.target.anim_delay = -1
        current_tile = self.target.map.layers['below'].get_at(*self.target.center)
        if current_tile is not None:
            self.target.set_position(current_tile.px, current_tile.py)

    def update(self, dt):
        pass

    def touch(self, *args):
        pass


class SelectAttackState(TurnAction):
    def __init__(self, target, **kwargs):
        super(SelectAttackState, self).__init__(target, **kwargs)
        self.amount = self.target.map.tile_width
        self.moving = False
        self.velocity = [0, 0]
        self.layer = self.target.map.layers.by_name['below']
        self.foreshadowed = self.layer.get_at(*target.center)
        self.move_keys = [Keyboard.keycodes['left'], Keyboard.keycodes['right'],
                          Keyboard.keycodes['up'], Keyboard.keycodes['down'], Keyboard.keycodes['enter']]
        self.travelled = set()
        self.checked = set()
        self.index = {}
        self.instructions = InstructionGroup()
        self.layer = self.target.map.layers.by_name['below']
        self.confirmed = False
        self.effect = MeleeDamage
        tile = self.layer.get_at(*self.target.pos)
        self.cursor = Sprite(pos=[tile.px, tile.py],
                             size=self.target.size, texture=images['cursor'], opacity=0.5)
        self.current_tile = self.target.get_current_cell()
        self.target.game.layer_widgets['sprite_layer'].add_widget(self.cursor)
        self.get_tiles_in_range(tile, 0)
        self.selected = None
        self.last_touched = None
        self.highlight_tiles()

    def highlight_tiles(self):
        for tile in self.travelled:
            self.instructions.add(Color(rgba=[1, .4, .3, .3]))
            self.instructions.add(Rectangle(pos=(tile.px, tile.py), size=(tile.px_width, tile.px_height)))
        self.target.game.layer_widgets['below'].canvas.add(self.instructions)
        # print(self.travelled, self.foreshadowed)

    @memoized
    def get_tiles_in_range(self, tile, moved):
        self.travelled.add(tile)
        if moved < 2:
            for neighbor in self.layer.get_neighbor_cells(tile):
                # if not self.target.map.layers['objects'].collide(Rect(*neighbor.center + (8, 8)), 'wall'):
                self.get_tiles_in_range(neighbor, moved + 1)

    def touch(self, touch, *args):
        print('touch!', touch)
        pos = self.target.map.pixel_from_screen(*touch.pos)
        cell = self.target.map.layers.by_name['below'].get_at(*pos)
        print('at {}.  Found?  {}'.format(pos, cell))
        if cell is not None and cell in self.travelled:
            print('cell not none, found in travels')
            self.cursor.pos = (cell.px, cell.py)
            if cell is self.last_touched:
                if self.get_selected():
                    self.confirm()
            else:
                self.last_touched = cell
                self.highlight_selected(cell)

    def highlight_selected(self, tile):
            if self.selected:
                for s in self.selected:
                    self.instructions.remove(s)
            self.selected = [Color(rgba=[6, .3, .2, .6]),
                             Rectangle(pos=(tile.px, tile.py), size=(tile.px_width, tile.px_height))]
            for a in self.selected:
                self.instructions.add(a)

    def get_selected(self):
        self.selected_targets = []
        for battler in self.target.game.entities:
            # TODO - figure out why this code is selecting both characters...
            print('checks say:', battler is not self.target, not battler.incapacitated,
                  self.cursor.collide_point(*battler.center))
            if battler is not self.target and not battler.incapacitated and self.cursor.collide_point(*battler.center):
                self.selected_targets.append(battler)
        print('selected targets:', self.selected_targets)
        return self.selected_targets

    def update(self, dt):
        if not self.confirmed:
            if not self.moving:
                self.velocity = [0, 0]
                if keys.get(Keyboard.keycodes['left']):
                    self.velocity = self.velocity_dict['left']
                elif keys.get(Keyboard.keycodes['right']):
                    self.velocity = self.velocity_dict['right']
                elif keys.get(Keyboard.keycodes['up']):
                    self.velocity = self.velocity_dict['up']
                elif keys.get(Keyboard.keycodes['down']):
                    self.velocity = self.velocity_dict['down']
                elif keys.get(Keyboard.keycodes['enter']):
                    print('battle_entities currently:', self.target.game.entities)
                    if self.get_selected():
                        self.confirm()
                    else:
                        pass
                elif keys.get(Keyboard.keycodes['backspace']):
                    print('pressed backspace')
                    self.end()
                else:
                    return
                new_x = self.current_tile.x + self.velocity[0]
                new_y = self.current_tile.y + self.velocity[1]
                # print('new not none')
                new_target = self.layer.get_tile(new_x, new_y)
                if new_target and new_target.tile.is_passable() and not new_target.occupied:
                    # print('starting to move!')
                    self.foreshadowed = new_target
                if self.foreshadowed in self.travelled:
                    self.start_moving()

            else:
                self.move(dt)
        else:
            if not self.current_effect.finished:
                self.current_effect.update(dt)
            else:
                self.ready_next_effect()

    def move(self, dt):
        # because we are moving a cursor Sprite and there's a dependency mess, we are pasting here for now
        x, y = self.foreshadowed.px, self.foreshadowed.py
        delta_x = self.cursor.x - x
        delta_y = self.cursor.y - y
        distance = Vector(*self.cursor.pos).distance((x, y))
        if distance >= 0.5:
            delta_x = (delta_x / distance) * (dt * 50)
            delta_y = (delta_y / distance) * (dt * 50)
            new_x, new_y = self.cursor.pos
            new_x += -delta_x
            new_y += -delta_y
            self.cursor.pos = [new_x, new_y]
            distance = Vector(*self.cursor.pos).distance((x, y))
        if distance <= 0.5:
            self.done_moving()
        else:
            return False

    def done_moving(self, *args):
        self.cursor.pos = [self.foreshadowed.px, self.foreshadowed.py]
        self.current_tile = self.foreshadowed
        self.moving = False

    def start_moving(self, *args):
        self.moving = True

    def end(self):
        super(SelectAttackState, self).end()
        self.target.state = BattleMenuState(self.target)
        self.target.game.layer_widgets['below'].canvas.remove(self.instructions)
        self.target.anim_delay = -1
        self.target.reload()  # reset animation
        self.cursor.parent.remove_widget(self.cursor)


class TurnEnd(State):
    def update(self, dt):
        print('turn end called!')
        self.target.game.get_next_turn_taker()
        self.end()

    def touch(self, touch):
        pass


class BattleMenuState(State):
    def __init__(self, target, **kwargs):
        super(BattleMenuState, self).__init__(target, **kwargs)
        print('battle menu state here, how ya doin', self, target)
        overlay = App.get_running_app().overlay
        self.move_button = Button(text='Move', on_release=lambda dt: self.change(SelectMoveState))
        self.attack_button = Button(text='Attack', on_release=lambda dt: self.change(SelectAttackState))
        self.wait_button = Button(text='Wait', on_release=lambda dt: self.change(TurnEnd))
        menu = GridLayout(cols=1, size_hint=(None, None), row_force_default=True, row_default_height=40)
        menu.width = dp(100)
        menu.height = menu.minimum_height
        buttons = [self.move_button, self.attack_button, self.wait_button]
        for button in buttons:
            menu.add_widget(button)
        menu.y = dp((Window.height / 2) + (menu.height / 2))
        menu.x = dp(40)
        self.menu = menu
        overlay.add_widget(self.menu)
        self.target.game.set_focus_target(self.target)

    def touch(self, touch):
        print('battle menu touched', self, self.target, touch)

    def update(self, dt):
        if keys.get(Keyboard.keycodes['m']):
            keys.pop(Keyboard.keycodes['m'])
            self.change(SelectMoveState)
        if keys.get(Keyboard.keycodes['a']):
            keys.pop(Keyboard.keycodes['a'])
            self.change(SelectAttackState)
        if keys.get(Keyboard.keycodes['w']):
            keys.pop(Keyboard.keycodes['w'])
            self.change(TurnEnd)

    def change(self, state):
        self.target.state = state(self.target)
        self.end()

    def end(self):
        print('end called', self.menu)
        super(BattleMenuState, self).end()
        if self.menu:
            self.menu.parent.remove_widget(self.menu)
            self.menu = None
        print('None?', self.menu)


class SelectMoveState(State):
    def __init__(self, target, **kwargs):
        super(SelectMoveState, self).__init__(target, **kwargs)
        self.amount = self.target.map.tile_width
        self.moving = False
        self.velocity = [0, 0]
        self.layer = self.target.map.layers.by_name['below']
        self.foreshadowed = self.layer.get_at(*target.center)
        self.current_tile = self.target.get_current_cell()
        self.move_keys = [Keyboard.keycodes['left'], Keyboard.keycodes['right'],
                          Keyboard.keycodes['up'], Keyboard.keycodes['down'], Keyboard.keycodes['enter']]
        self.travelled = set()
        self.checked = set()
        self.index = {}
        self.instructions = InstructionGroup()
        self.layer = self.target.map.layers.by_name['below']
        tile = self.layer.get_at(*self.target.pos)
        self.get_tiles_in_range(tile, 0)
        self.last_touched = None
        self.selected = []
        self.highlight_tiles()

    def touch(self, touch, *args):
        print('touch!', touch)
        pos = self.target.map.pixel_from_screen(*touch.pos)
        cell = self.target.map.layers.by_name['below'].get_at(*pos)
        print('at {}.  Found?  {}'.format(pos, cell))
        if cell is not None and cell in self.travelled:
            print('cell not none, found in travels')
            if cell is self.last_touched:
                self.target.set_position(cell.px, cell.py)
                self.end()
            else:
                self.last_touched = cell
                self.highlight_selected(cell)

    def highlight_selected(self, tile):
            if self.selected:
                for s in self.selected:
                    self.instructions.remove(s)
            self.selected = [Color(rgba=[6, .3, .2, .6]),
                             Rectangle(pos=(tile.px, tile.py), size=(tile.px_width, tile.px_height))]
            for a in self.selected:
                self.instructions.add(a)

    def highlight_tiles(self):
        for tile in self.travelled:
            self.instructions.add(Color(rgba=[.3, .5, .8, .5]))
            self.instructions.add(Rectangle(pos=(tile.px, tile.py), size=(tile.px_width, tile.px_height)))
        self.target.game.layer_widgets['below'].canvas.add(self.instructions)

    @memoized
    def get_tiles_in_range(self, tile, moved):
        self.travelled.add(tile)
        # did this to keep smallest range possible to reach selected tile, for calculating cost at end of move state
        self.index[tile] = min(self.index.get(tile, 1000), moved)
        if moved < self.target.move_range():
            for neighbor in self.layer.get_neighbor_cells(tile):
                self.get_tiles_in_range(neighbor, moved + 1)

    def update(self, dt):
        if not self.moving:
            pressed = [key for key in self.move_keys if keys.get(key)]
            if pressed:
                self.velocity = [0, 0]
                if Keyboard.keycodes['left'] in pressed:
                    self.target.set_face('left')
                    self.velocity = self.velocity_dict['left']
                elif Keyboard.keycodes['right'] in pressed:
                    self.target.set_face('right')
                    self.velocity = self.velocity_dict['right']
                elif Keyboard.keycodes['up'] in pressed:
                    self.target.set_face('up')
                    self.velocity = self.velocity_dict['up']
                elif Keyboard.keycodes['down'] in pressed:
                    self.target.set_face('down')
                    self.velocity = self.velocity_dict['down']
                elif keys.get(Keyboard.keycodes['enter']):
                    self.end()
                    return
                self.current_tile = self.target.get_current_cell()
                new_x = self.current_tile.x + self.velocity[0]
                new_y = self.current_tile.y + self.velocity[1]
                # print('new not none')
                new_target = self.layer.get_tile(new_x, new_y)
                if new_target and new_target.tile.is_passable() and not new_target.occupied:
                    # print('starting to move!')
                    self.foreshadowed = new_target
                if self.foreshadowed in self.travelled:
                    self.start_moving()
            else:
                if self.target.anim_delay > 0:
                    self.target.reload()  # reset animation
                self.target.anim_delay = -1
        else:
            self.move(dt)

    def move(self, dt):
        done = move(dt, self.target, self.foreshadowed.px, self.foreshadowed.py)
        if done:
            self.done_moving()

    def done_moving(self, *args):
        self.target.set_position(self.foreshadowed.px, self.foreshadowed.py)
        self.moving = False

    def start_moving(self, *args):
        self.moving = True

    def end(self):
        current = self.layer.get_at(*self.target.center)
        self.target.spend_moves(self.index[self.layer.get_at(*self.target.center)])
        self.target.game.layer_widgets['below'].canvas.remove(self.instructions)
        self.target.anim_delay = -1
        self.target.reload()  # reset animation
        self.target.set_position(current.px, current.py)
        self.target.state = BattleMenuState(self.target)
