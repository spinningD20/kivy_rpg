from random import uniform, randrange

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Keyboard
from kivy.graphics.context_instructions import Color
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics.vertex_instructions import Rectangle
from kivy.vector import Vector

from helpers import keys
from states.state import State, move
from states.turn import WaitingForTurn


class IdleReadyState(State):
    def __init__(self, target):
        super(IdleReadyState, self).__init__(target)
        self.move_keys = [Keyboard.keycodes['left'], Keyboard.keycodes['right'],
                          Keyboard.keycodes['up'], Keyboard.keycodes['down']]
        # print('angle', self.target.body.angle)
        self.target.get_current_cell()
        self.target.anim_delay = -1
        self.target.reload()
        # self.instructions = InstructionGroup()
        # self.instructions.add(Color(rgba=[.25, .8, .8, 1]))
        # points = [(p.x, p.y) for p in self.target.shape.get_vertices()]
        # points.append(points[0])
        # self.instructions.add(Line(points=points, width=2))
        # # points = [(p.x, p.y) for p in self.target.interactor.get_vertices()]
        # # points.append(points[0])
        # # self.instructions.add(Line(points=points, width=2))
        # self.target.game.layer_widgets['sprite_layer'].canvas.add(self.instructions)
        self.target.activate_object(target='floor', button_press=False)

    def highlight_tiles(self, tiles):
        self.instructions.clear()
        for tile in tiles:
            self.instructions.add(Color(rgba=[1, .4, .3, .3]))
            self.instructions.add(Rectangle(pos=(tile.px, tile.py), size=(tile.px_width, tile.px_height)))
        self.target.game.layer_widgets['below'].canvas.add(self.instructions)

    def update(self, dt):
        if keys.get(Keyboard.keycodes['tab']):
            keys.pop(Keyboard.keycodes['tab'])
            self.target.state = WaitingForTurn(self.target)
            self.end()
            self.target.game.cycle_character()
            return
        elif keys.get(Keyboard.keycodes['n']):
            keys.pop(Keyboard.keycodes['n'])
            print(len(self.target.game.space.nearest_point_query(self.target.body.position, 256, layers=-1, group=0)))
        elif keys.get(Keyboard.keycodes['enter']):
            keys.pop(Keyboard.keycodes['enter'])
            self.target.activate_object()
        elif keys.get(Keyboard.keycodes['c']):
            keys.pop(Keyboard.keycodes['c'])
            print('player', len(self.target.game.space.shapes))
        elif keys.get(Keyboard.keycodes['v']):
            keys.pop(Keyboard.keycodes['v'])
            scalar = App.get_running_app().manager.current_screen.ids.scalar
            if scalar.scale < 5:
                scalar.scale += 1
        elif keys.get(Keyboard.keycodes['b']):
            keys.pop(Keyboard.keycodes['b'])
            scalar = App.get_running_app().manager.current_screen.ids.scalar
            if scalar.scale > 2:
                scalar.scale -= 1
        else:
            for k in [key for key in self.move_keys if keys.get(key)]:
                # self.instructions.clear()
                self.target.state = RealtimeMove(self.target)
                self.end()
                break

    def touch(self, touch, *args):
        pos = self.target.map.pixel_from_screen(*touch.pos)
        cell = self.target.map.layers.by_name['below'].get_at(*pos)
        origin_cell = self.target.map.layers.by_name['below'].get_at(*self.target.pos)

        if cell is not None and cell.tile.is_passable():
            cells = cell.layer.a_star_search(origin_cell, cell)
            if len(cells) == 2 and cell not in self.target.map.layers.by_name['below'].get_neighbor_cells(origin_cell):
                return
            cells.remove(origin_cell)
            cells.reverse()
            # self.highlight_tiles(cells)
            self.target.state = RealtimeTouchMove(self.target, cells)
            self.end()
        if cell == origin_cell:
            print(self.target.pos, self.target.body.position, self.target.shape.get_vertices())

    # def end(self, *args):
    #     self.instructions.clear()
    #     print('called')


class RealtimeTouchMove(State):
    def __init__(self, target, cells, **kwargs):
        super(RealtimeTouchMove, self).__init__(target, **kwargs)
        self.cells = cells
        self.moving = False
        self.instructions = InstructionGroup()
        self.highlight_tiles(cells)
        self.foreshadowed = self.target._current_cell
        self.velocity = [0, 0]
        self.target.anim_delay = .2
        self.movement_axis = 0

    def touch(self, touch, *args):
        pos = self.target.map.pixel_from_screen(*touch.pos)
        cell = self.target.map.layers.by_name['below'].get_at(*pos)
        origin_cell = self.target.map.layers.by_name['below'].get_at(*self.target.pos)

        if cell is not None and cell.tile.is_passable():
            cells = cell.layer.a_star_search(origin_cell, cell)
            # if there's only two cells selected, and goal is not origin neighbor... then run away, RUN AWAY!
            if len(cells) == 2 and cell not in self.target.map.layers.by_name['below'].get_neighbor_cells(origin_cell):
                return
            if len(cells) > 1:
                cells.reverse()
                self.instructions.clear()
                self.instructions = InstructionGroup()
                self.highlight_tiles(cells)
                self.cells = cells
                self.moving = False

    def update(self, dt):
        if not self.moving:
            self.check_moving()
        else:
            self.move(dt)

    def move(self, dt):
        delta_x = self.target.x - self.foreshadowed.px
        delta_y = self.target.y - self.foreshadowed.py
        distance = Vector(*self.target.pos).distance((self.foreshadowed.px, self.foreshadowed.py))
        if distance >= 1.0:
            delta_x = (delta_x / distance) * (dt * 50)
            delta_y = (delta_y / distance) * (dt * 50)
            x, y = self.target.pos
            x += -delta_x
            y += -delta_y
            self.target.set_position(x, y)
            distance = Vector(*self.target.pos).distance((self.foreshadowed.px, self.foreshadowed.py))
        if distance <= 1.0:
            self.check_moving()

    def done_moving(self, *args):
        self.target.set_position(self.foreshadowed.px, self.foreshadowed.py)
        self.moving = False

    def highlight_tiles(self, tiles):
        self.instructions.clear()
        for tile in tiles:
            self.instructions.add(Color(rgba=[.3, 1, .3, .3]))
            self.instructions.add(Rectangle(pos=(tile.px, tile.py), size=(tile.px_width, tile.px_height)))
        self.target.game.layer_widgets['below'].canvas.add(self.instructions)

    def check_moving(self, *args):
        last_axis = self.movement_axis
        last_cell = self.foreshadowed
        if self.cells:
            self.moving = True
            self.foreshadowed = self.cells.pop()
            print('moving to', self.foreshadowed.bottomleft)
            if self.foreshadowed.px != last_cell.px:
                self.movement_axis = 0
                if self.foreshadowed.px < last_cell.px:
                    self.target.set_face('left')
                    self.velocity = [self.target.map.tile_width * -1, 0]
                else:
                    self.target.set_face('right')
                    self.velocity = [self.target.map.tile_width, 0]
            elif self.foreshadowed.py != last_cell.py:
                self.movement_axis = 1
                if self.foreshadowed.py < last_cell.py:
                    self.target.set_face('down')
                    self.velocity = [0, self.target.map.tile_width * -1]
                else:
                    self.target.set_face('up')
                    self.velocity = [0, self.target.map.tile_width]
            if last_axis != self.movement_axis:
                print('axis changed!')
                print(self.target.pos)
                self.target.set_position(last_cell.px, last_cell.py)
                print(self.target.pos)
                print(last_cell.bottomleft, self.foreshadowed.bottomleft)

        else:
            self.done_moving()
            self.end()
            print('no cells')
            return
        self.target.activate_object(target='floor', button_press=False)

    def end(self):
        self.target.state = IdleReadyState(self.target)
        self.instructions.clear()


# TODO - make anim_delay (animation speed) and tile movement Animation's duration integrated with equation.


class RealtimeMove(State):
    def __init__(self, target):
        super(RealtimeMove, self).__init__(target)
        self.amount = self.target.map.tile_width
        self.moving = False
        self.layer = self.target.map.layers.by_name['below']
        self.foreshadowed = self.layer.get_at(*target.center)
        self.move_keys = [Keyboard.keycodes['left'], Keyboard.keycodes['right'],
                          Keyboard.keycodes['up'], Keyboard.keycodes['down']]
        self.direction = self.target.facing
        self.current_tile = self.target.get_current_cell()
        self.velocity = self.velocity_dict['idle']
        self.pressed = None
        self.target.anim_delay = .2  # here because changing delay on start/done weirds things up
        self.start_moving()

    def update(self, dt):
        self.pressed = [key for key in self.move_keys if keys.get(key)]
        if not self.moving:
            # print('not moving')
            self.check_moving()
        else:
            # print('!!!')
            self.move(dt)

    def move(self, dt):
        done = move(dt, self.target, self.foreshadowed.px, self.foreshadowed.py)
        if done:
            self.check_moving()

    def check_moving(self):
        # print('checking movement')
        if self.pressed:
            if Keyboard.keycodes['left'] in self.pressed:
                self.target.set_face('left')
                self.velocity = self.velocity_dict['left']
            elif Keyboard.keycodes['right'] in self.pressed:
                self.target.set_face('right')
                self.velocity = self.velocity_dict['right']
            elif Keyboard.keycodes['up'] in self.pressed:
                self.target.set_face('up')
                self.velocity = self.velocity_dict['up']
            elif Keyboard.keycodes['down'] in self.pressed:
                self.target.set_face('down')
                self.velocity = self.velocity_dict['down']
            self.current_tile = self.target.get_current_cell()
            new_x = self.current_tile.x + self.velocity[0]
            new_y = self.current_tile.y + self.velocity[1]
            # print('new not none')
            new_target = self.layer.get_tile(new_x, new_y)
            if new_target and new_target.tile.is_passable() and not new_target.occupied:
                # print('starting to move!')
                self.foreshadowed = new_target
        else:
            self.target.set_position(self.foreshadowed.px, self.foreshadowed.py)
            self.target.state = IdleReadyState(self.target)
            self.target.reload()  # reset animation
            self.target.anim_delay = -1  # here because changing delay on start/done weirds things up
        self.target.activate_object(target='floor', button_press=False)

    def done_moving(self, *args):
        self.target.get_current_cell()
        self.moving = False

    def start_moving(self, *args):
        # print('start move hit')
        self.target.get_current_cell()
        self.moving = True

    def touch(self, touch):
        pass



class EntityIdle(State):
    def __init__(self, target, **kwargs):
        super(EntityIdle, self).__init__(target, **kwargs)
        # print('entity idle start')
        # print('idle started')
        self.scheduled = False
        self.do_wander = False
        self.task = None
        self.target.get_current_cell()
        # self.target.map.layers['below'].get_at(*self.target.pos).occupied = True
        self.target.anim_delay = -1  # here because changing delay on start/done weirds things up
        # self.instructions = InstructionGroup()
        # self.instructions.add(Color(rgba=[1, .3, .3, 1]))
        # points = [(p.x, p.y) for p in self.target.shape.get_vertices()]
        # points.append(points[0])
        # self.instructions.add(Line(points=points, width=2))
        # # print('entity', self.target.shape.get_vertices())
        # # points = [(p.x, p.y) for p in self.target.detector.get_vertices()]
        # # points.append(points[0])
        # # self.instructions.add(Line(points=points, width=2))
        # self.target.game.layer_widgets['sprite_layer'].canvas.add(self.instructions)

    def update(self, dt):
        if not self.scheduled:
            self.scheduled = True
            self.target.set_position(self.target.data.x, self.target.data.y)
            delay = uniform(2.0, 2.5)
            self.task = Clock.schedule_once(lambda *args: self.toggle_wander(), delay)
            # print('rect\' em!', self.target.detector.get_vertices(), player.pos)
            # if Rect(*player.pos + player.size).intersect(self.target.detector):
            #     los = Rect(min(player.center_x, self.target.center_x),
            #                min(player.center_y, self.target.center_y),
            #                abs(player.center_x - self.target.center_x),
            #                abs(player.center_y - self.target.center_y))
            #     between = self.target.map.layers['walls'].collide(los, 'wall')
            #     if not between:
            #         print(player.pos, player.size, self.target.detector.corners(), self.target.detector.size)
            #         if self.task:
            #             self.task.cancel()
            #         self.end()
            #         self.target.state = EntityFollow(self.target, player)
            #         return
        elif self.do_wander:
            layer = self.target.map.layers['below']
            current_cell = layer.get_at(*self.target.pos)
            cell_options = list(layer.get_neighbor_cells(current_cell))
            if cell_options:
                if len(cell_options) - 1 == 0:
                    selected = cell_options[0]
                else:
                    selected_range = randrange(0, len(cell_options))
                    selected = cell_options[selected_range]
                    # print(len(cell_options), selected_range)
                    self.target.state = EntityWander(self.target, selected)
                    self.end()
            else:
                self.scheduled = False

    def toggle_wander(self):
        self.do_wander = True

    def end(self):
        # self.instructions.clear()
        if self.task:
            self.task.cancel()


class EntityFollow(State):
    def __init__(self, target, following):
        super(EntityFollow, self).__init__(target)
        self.following = following
        self.cells = []
        self.moving = False
        self.instructions = InstructionGroup()
        targeted = self.target.map.layers.by_name['below'].get_at(*self.following.pos)
        # targeted = self.target.map.layers.by_name['below'].get_neighbor_cells(following_cell)[0]
        origin_cell = self.target.map.layers.by_name['below'].get_at(*self.target.pos)

        if targeted is not None and targeted.tile.is_passable():
            cells = targeted.layer.a_star_search(origin_cell, targeted)
            # if there's only two cells selected, and goal is not origin neighbor... then run away, RUN AWAY!
            if len(cells) == 2 and targeted not in self.target.map.layers.by_name['below'].get_neighbor_cells(origin_cell):
                return
            if len(cells) > 1:
                cells.reverse()
                # self.instructions.clear()
                self.instructions = InstructionGroup()
                # self.highlight_tiles(cells)
                self.cells = cells
                self.moving = False
        if not self.cells:
            print('no cells here dawg')
            self.target.state = EntityIdle(self.target)
            self.end()
            return
        # self.highlight_tiles(self.cells)
        self.foreshadowed = None
        self.velocity = [0, 0]
        self.target.anim_delay = .2
        self.task = Clock.schedule_interval(self.slow_update, .6)

    def slow_update(self, *args):
        print([self.following.pos])
        distance = Vector(*self.target.pos).distance(self.following.pos)
        if distance < 100:
            pass
        else:
            self.moving = False
            # self.instructions.clear()
            self.target.set_position(self.foreshadowed.px, self.foreshadowed.py)
            if distance > 500:
                self.target.state = EntityIdle(self.target)
                self.end()
            else:
                self.target.state = EntityFollow(self.target, self.following)
                self.end()

    def update(self, dt):
        if not self.moving:
            if self.cells:
                self.foreshadowed = self.cells.pop()
                print('moving to', self.foreshadowed)
                # if self.foreshadowed.occupied:
                #     self.end()
                if self.foreshadowed.px != self.target.x:
                    if self.foreshadowed.px < self.target.x:
                        self.target.set_face('left')
                        self.velocity = [self.target.map.tile_width * -1, 0]
                    else:
                        self.target.set_face('right')
                        self.velocity = [self.target.map.tile_width, 0]
                elif self.foreshadowed.py != self.target.y:
                    if self.foreshadowed.py < self.target.y:
                        self.target.set_face('down')
                        self.velocity = [0, self.target.map.tile_width * -1]
                    else:
                        self.target.set_face('up')
                        self.velocity = [0, self.target.map.tile_width]
                self.start_moving()
            else:
                self.end()
                self.target.get_current_cell()
                self.target.state = EntityIdle(self.target)
        else:
            self.move(dt)

    def move(self, dt):
        done = move(dt, self.target, self.foreshadowed.px, self.foreshadowed.py)
        if done:
            self.done_moving()

    def done_moving(self, *args):
        self.target.set_position(self.foreshadowed.px, self.foreshadowed.py)
        self.moving = False

    def highlight_tiles(self, tiles):
        self.instructions.clear()
        for tile in tiles:
            self.instructions.add(Color(rgba=[.3, 1, .3, .3]))
            self.instructions.add(Rectangle(pos=(tile.px, tile.py), size=(tile.px_width, tile.px_height)))
        self.target.game.layer_widgets['below'].canvas.add(self.instructions)

    def start_moving(self, *args):
        print('start moving')
        self.moving = True

    def end(self):
        super(EntityFollow, self).end()
        self.task.cancel()
        # self.instructions.clear()


class EntityWander(State):
    def __init__(self, target, cell):
        super(EntityWander, self).__init__(target)
        # print('wander started')
        self.moving = True
        self.velocity = [0, 0]
        if cell.px != target.x:
            if cell.px < target.x:
                self.target.set_face('left')
                self.velocity[0] = self.target.map.tile_width * -1
            else:
                self.target.set_face('right')
                self.velocity[0] = self.target.map.tile_width
        elif cell.py != target.y:
            if cell.py < target.y:
                self.target.set_face('down')
                self.velocity[1] = self.target.map.tile_width * -1
            else:
                self.target.set_face('up')
                self.velocity[1] = self.target.map.tile_width
        self.foreshadowed = cell
        current_cell = self.target.map.layers['below'].get_at(*self.target.pos)
        self.target.anim_delay = .2  # here because changing delay on start/done weirds things up
            # cell.occupied = True
        # self.instructions = InstructionGroup()
        # self.instructions.add(Color(rgba=[1, .4, .3, .5]))
        # self.instructions.add(Rectangle(pos=(cell.px, cell.py), size=(cell.px_width, cell.px_width)))
        # self.instructions.add(Color(rgba=[0, 1, 1, .5]))
        # self.instructions.add(Rectangle(pos=(current_cell.px, current_cell.py), size=(current_cell.px_width, current_cell.px_width)))
        # self.target.game.layer_widgets['below'].canvas.add(self.instructions)
        if cell.occupied:
            self.moving = False
            self.target.state = EntityIdle(self.target)

    def update(self, dt):
        if not self.moving:
            self.target.state = EntityIdle(self.target)
            self.end()
        else:
            self.move(dt)

    def move(self, dt):
        done = move(dt, self.target, self.foreshadowed.px, self.foreshadowed.py)
        if done:
            self.done_moving()

    def done_moving(self, *args):
        self.target.set_position(self.foreshadowed.px, self.foreshadowed.py)
        self.moving = False
        self.target.reload()
        # self.instructions.clear()

    def start_moving(self, *args):
        self.moving = True

    # def end(self):
    #     super(EntityWander, self).end()
        # if self.instructions:
        #     self.instructions.clear()