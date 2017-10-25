from kivy.animation import Animation
from kivy.event import EventDispatcher
from kivy.uix.button import Button


class Effect(EventDispatcher):
    # the strategy for multiple effects hit one target from an action
    # is to have children effects within the primary effect.
    # this is mostly here as a base class to exhibit what the subclass is, and leave spot for changing all.
    def __init__(self, target, **kwargs):
        self.target = target
        self.register_event_type('on_end')
        super(Effect, self).__init__()

    def update(self, dt):
        pass

    def end(self):
        self.dispatch('on_end')

    def on_end(self, *args):
        print('on end dispatched! effect')
        pass


class MeleeDamage(Effect):
    def __init__(self, target, **kwargs):
        print('melee spawned, target is', target)
        super(MeleeDamage, self).__init__(target, **kwargs)
        self.finished = False
        self.damage_amount = -25  # some lengthy bit here for an equation
        self.layer = self.target.map.layers.by_name['below']
        tile = self.layer.get_at(*self.target.pos)
        self.display = Button(text=str(self.damage_amount), size_hint=(None, None),
                              size=(target.map.tile_width / 2, target.map.tile_width / 2),
                              pos=self.target.pos)
        self.target.parent.add_widget(self.display)
        self.animation = Animation(y=(self.target.y + self.target.map.tile_width), duration=.7)
        self.animation &= Animation(opacity=0.0, duration=.7)
        self.animation.bind(on_complete=self.complete)
        self.animation.start(self.display)

    def update(self, dt):
        if self.finished:
            self.end()

    def complete(self, *args):
        self.finished = True
        self.display.parent.remove_widget(self.display)
        # TODO - since updating so that properties are related in db, need to rework property get/set code.
        # print('hit points were', self.target.properties['current_hit_points'])
        # self.target.properties['current_hit_points'] += self.damage_amount
        # print('hit points now', self.target.properties['current_hit_points'])
        # print('completed melee damage effect')
        self.end()

    def end(self, *args):
        # if self.target.data['current_hit_points'] <= 0:
        #     self.target.incapacitated = True
        self.dispatch('on_end')
