from xml.etree import cElementTree as ElementTree
import os
import fnmatch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import TileMap, MapObject, MapObjectProperty, Base


engine = create_engine('sqlite:///seed.db')
Session = sessionmaker(bind=engine)
db = Session()


def map_tmx_to_db(xml_element, xml_file_name):
    db_map = db.query(TileMap).filter(TileMap.file_name == xml_file_name).first()
    map_x = xml_element.attrib['width']
    map_y = xml_element.attrib['height']
    # print(map_x, map_y)
    if not db_map:
        # print('adding new map')
        db_map = TileMap()
        fog_of_war = {}
        for x in range(int(map_x)):
            for y in range(int(map_y)):
                fog_of_war.update({(x, y): True})

        db_map.file_name = xml_file_name
    db_map.full_name = 'get later from tmx attrib, somehow...'
    db_map.width = map_x
    db_map.height = map_y
    db.add(db_map)
    db_map.load()
    db.commit()
    return db_map


def map_objects_tmx_to_db(tmx_map, db_map):
    db_map_objects = db.query(MapObject).filter(MapObject.map_id == db_map.id)
    object_list = []
    for map_object in db_map_objects:
        object_list.append(map_object)
    # # print(len(object_list))
    object_list_copy = list(object_list)
    tmx_object_group = tmx_map.find('objectgroup')
    if tmx_object_group:
        for tmx_object in tmx_object_group:
            # print(tmx_map, tmx_object.items(), tmx_object.keys())
            # # print(tmx_object.attrib)
            x = float(tmx_object.attrib['x'])
            print('name:', tmx_object.attrib['name'])
            print('x is', x)
            print('flipping y from', tmx_map.attrib['height'], tmx_map.attrib['tileheight'], tmx_object.attrib['y'])
            y = ((int(tmx_map.attrib['height']) * int(tmx_map.attrib['tileheight'])) - float(tmx_object.attrib['y']) - int(tmx_object.attrib['height']))
            print('to', y)
            # print(x, y)
            db_object = None
            for o in object_list_copy:
                if str(o.name).lower() == str(tmx_object.attrib['name']).lower():
                    db_object = o
                    object_list.remove(o) if o in object_list else object_list
            if not db_object:
                # print('adding new object')
                db_object = MapObject()
                db_object.map_id = db_map.id
                db_object.name = str(tmx_object.attrib['name'])
            db_object.type = tmx_object.attrib['type']
            db_object.width, db_object.height = tmx_object.attrib['width'], tmx_object.attrib['height']
            db_object.x, db_object.y = (x, y)
            db.add(db_object)
            db.commit()
            map_object_properties_tmx_to_db(tmx_object, db_object)
        if len(object_list) > 0: # if something was removed in tmx, or in db but not in tmx, remove it from db!
            for o in object_list:
                db.delete(o)
            db.commit()
    return True


def map_object_properties_tmx_to_db(tmx_object, db_object):
    db_map_object_properties = db.query(MapObjectProperty).filter(
        MapObjectProperty.object_id == db_object.id)
    object_properties_list = []
    for o_prop in db_map_object_properties:
        object_properties_list.append(o_prop)
    # # print(len(object_properties_list))
    object_properties_list_copy = list(object_properties_list)
    tmx_object_properties = tmx_object.find('properties')
    if tmx_object_properties:
        for object_property in tmx_object_properties:
            # # print(object_property.attrib)
            db_map_object_property = None
            for op in object_properties_list_copy:
                # # print(str(op.property).lower(), str(object_property.attrib['name']).lower())
                if str(op.property).lower() == str(object_property.attrib['name']).lower():
                    db_map_object_property = op
                    object_properties_list.remove(op)
            if not db_map_object_property:
                # print('adding new map property...')
                db_map_object_property = MapObjectProperty()
                db_map_object_property.object_id = db_object.id
                db_map_object_property.property = object_property.attrib['name']
                # print(object_property.attrib.get('value'))
                # print(object_property.attrib['name'])
            db_map_object_property.value = object_property.attrib['value']
            db.add(db_map_object_property)
            db.commit()
        if len(object_properties_list) > 0: # if something was removed in tmx, or in db but not in tmx, remove it from db!
            for op in object_properties_list:
                db.delete(op)
            db.commit()


def all_tmx_files_to_db():
    Base.metadata.create_all(engine)
    # print(datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S'))
    for rootdir, dir, files in os.walk(os.path.dirname(os.path.abspath(__file__))+str('/maps/')):
        # this is going on for each recursive subdirectory - we don't want that.  research better filename retrieval
        # # print(os.listdir(os.path.dirname(os.path.abspath(__file__))+str('/maps'))) - didn't work
        # print(rootdir, dir, files)
        for current_file in fnmatch.filter(files, "*.tmx"):
            map_file = rootdir + current_file
            print('working on map', map_file)
            with open(map_file) as f:
                root = ElementTree.parse(f).getroot()
                current_map = map_tmx_to_db(root, current_file)
                current_objects = map_objects_tmx_to_db(root, current_map)
                db.commit()
    # print(datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S'))

if __name__ == '__main__':
    all_tmx_files_to_db()
