from xml.etree import ElementTree

from kivy.app import App
from kivy.core.window import Keyboard

from helpers import keys
from models import TileMap, MapObject
from widgets.ui import DialogueBox


class Dialogue(object):
    def __init__(self, game, xml):
        # consider text speed for displaying text instead of all at once.  do all at once for now.
        self.text = xml.attrib.get('text', "I'd say something smarter if you put it in the XML.")
        self.name = xml.attrib.get('name', 'No Name Found in XML')
        self.ended = False
        self.box = DialogueBox(self.text, self.name, on_dismiss=lambda x: setattr(self, 'ended', True))
        self.open = False

    def update(self, dt):
        if not self.open:
            self.open = True
            self.box.open()
        if keys.get(Keyboard.keycodes['enter']):
            keys.pop(Keyboard.keycodes['enter'])
            if self.box.parent:
                self.box.dismiss()


class MapChange(object):
    def __init__(self, game, xml):
        tilemap = App.get_running_app().db.query(TileMap).filter(TileMap.file_name == xml.attrib['map_name']).first()
        print(ElementTree.tostring(xml))
        print(xml.attrib['map_name'])
        print(xml.attrib['entrance_name'])
        print(tilemap.id)
        if tilemap:
            entrance = App.get_running_app().db.query(MapObject).filter(MapObject.map_id == tilemap.id, MapObject.name == xml.attrib['entrance_name']).first()
            if entrance:
                print('entrance found')
                db = App.get_running_app().db
                changes = dict(map_id=tilemap.id, x=entrance.x, y=entrance.y)
                for player in game.player_characters:
                    for prop in changes:
                        setattr(player.data, prop, changes[prop])
                    db.add(player.data)
                    db.commit()
                map_name = xml.attrib['map_name']
                entrance_name = xml.attrib['entrance_name']
                game.save_data()
                App.get_running_app().load_map(map_name, entrance_name)
        self.ended = True

    def update(self, dt):
        if not self.ended:
            self.ended = True


events_by_key = {'dialogue': Dialogue, 'map_change': MapChange}


class EventSet(object):
    def __init__(self, xml, game):
        self.queued_events = []
        self.pausing = True if xml.attrib.get('pausing') in (None, 'true') else False
        self.current_event = None
        self.game = game
        for action_xml in sorted(xml.findall('action'), key=lambda s: s.attrib['order']):
            self.queued_events.append(events_by_key[action_xml.attrib['type']](self.game, action_xml))
        if self.queued_events:
            self.current_event = self.queued_events.pop(0)

    def update(self, dt):
        if self.current_event and not self.current_event.ended:
            self.current_event.update(dt)
        else:
            if self.queued_events:
                self.current_event = self.queued_events.pop(0)
            else:
                self.game.event_in_progress = None