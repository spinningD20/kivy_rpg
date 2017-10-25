from kivy.event import EventDispatcher
from kivy.vector import Vector


class State(EventDispatcher):
    target = None

    def __init__(self, target, **kwargs):
        self.register_event_type('on_end')
        self.instructions = None
        super(State, self).__init__(**kwargs)
        self.target = target
        self.ended = False
        self.velocity_dict = {
            'idle': [0, 0],
            'left': [-1, 0],
            'right': [1, 0],
            'up': [0, -1],
            'down': [0, 1]
        }

    def update(self, dt):
        pass

    def end(self, *args):
        self.ended = True
        del self

    def on_end(self, *args):
        pass


def move(dt, target, x, y):
    delta_x = target.x - x
    delta_y = target.y - y
    distance = Vector(*target.pos).distance((x, y))
    if distance >= 0.5:
        delta_x = (delta_x / distance) * (dt * 50)
        delta_y = (delta_y / distance) * (dt * 50)
        new_x, new_y = target.pos
        new_x += -delta_x
        new_y += -delta_y
        target.set_position(new_x, new_y)
        distance = Vector(*target.pos).distance((x, y))
    if distance <= 0.5:
        return True
    else:
        return False