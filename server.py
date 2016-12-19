#!/usr/bin/python
#    server.py - MQTT request processor and addressor
#    Copyright (C) 2016 Danya Generalov

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import paho.mqtt.client as mqtt
import json
import time
import os
import threading
import geopy
import uuid
import geopy.distance
global to_cancel
to_cancel = []
conf = json.load(open("./config.json"))
global log
try:
    log = json.load(open(conf["path_to_log"]))["log"]
except:
    log = []
global messages
messages = 0


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        global connected
        connected = True


def on_disconnect(client, userdata, rc):
    if rc:
        global connected
        connected = False
        connect()


def connect():
    global connected
    global m
    attempt = 0
    while not connected:
        attempt += 1
        try:
            m = mqtt.Client()
            m.on_connect = on_connect
            m.on_disconnect = on_disconnect
            m.connect("127.0.0.1")
            for i in ("data_chan", "event_chan", "reply_chan", "cancel_chan"):
                m.subscribe(conf[i])
            m.loop_start()
        except:
            pass

m = None
on_disconnect()
m.on_connect = on_connect
m.on_disconnect = on_disconnect


class Event:
    """This class defines an Event."""
    def __getitem__(self, item):
        return None

    def import_dict(self, dic):
        self.euid = str(dic["euid"])
        self.uuid = str(dic["uuid"])
        self.timestamp = dic["timestamp"]
        self.level = dic["level"]
        self.location = dic["location"]

    def export_dict(self):
        dic = dict()
        for i in ("euid", "uuid", "timestamp", "level", "location"):
            dic[i] = object.__getattr__(self, i)
        return dic

    def __init__(self, dic=None):
        self.timestamp = 0
        self.uuid = "00000000-0000-0000-0000-000000000000"
        self.euid = self.uuid
        if dic is not None:
            if not isinstance(dic, dict):
                raise TypeError("Expected type dict, but got " +
                                str(type(dic)) + " instead")
            else:
                self.import_dict(dic)

    def save(self):
        global conf
        output = {"timestamp": self.timestamp,
                  "uuid": self.uuid, "euid": self.euid}
        json.dump(output, open(
            conf["path_to_event_dir"] + self.uuid + ".json", "w"))

global events
events = []
for i in os.listdir(conf["path_to_event_dir"]):
    try:
        events += [Event(i)]
    except:
        pass


class EventHandler:
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == "long":
            object.__setattr__(self, "location", [self.location[0], value])
        elif name == "lat":
            object.__setattr__(self, "location", [value, self.location[1]])
        elif name == "location":
            object.__setattr__(self, "lat", value[0])
            object.__setattr__(self, "long", value[1])

    def get_distance_to(self, loc):
        return geopy.distance.vincenty(self.location, loc).meters

    def __init__(self, json_obj=None):
        self.location = [0, 0]
        self.levels = [1, 2, 3]
        self.uuid = "00000000-0000-0000-0000-000000000000"
        self.name = ""
        if isinstance(json_obj, dict):
            for i in json_obj:
                self.__setattr__(i, json_obj[i])

    def save(self):
        global conf
        output = {"location": self.location, "levels": self.level,
                  "uuid": self.uuid, "name": self.name}
        json.dump(output, open(conf["path_to_event_handlers_dir"] + str(
            uuid.uuid3(uuid.UUID("00000000-0000-0000-0000-000000000000"),
                       self.name)) + ".json", "w"))

global event_handlers
event_handlers = []
for i in os.listdir(conf["path_to_event_handlers_dir"]):
    try:
        event_handlers += [EventHandler(i)]
    except:
        pass


def cancelmoose():
    global events
    global conf
    global to_cancel
    to_cancel = []
    while 1:
        for i in events:
            if i.timestamp + \
              conf["time_to_cancel"]["l" + str(i.level)] < time.time():
                try:
                    to_cancel.remove(i)
                except:
                    pass
                if conf["debug"]:
                    print("Event of level", str(i.level), "from user ID",
                          i.uuid, "with ID", i.euid,
                          "is canceled due to timeout")
                events.remove(i)
            if i in to_cancel:
                to_cancel.remove(i)
                if conf["debug"]:
                    print("Event of level", str(i.level), "from user ID",
                          i.uuid, "with ID", i.euid,
                          "is canceled because of request")
                events.remove(i)
        time.sleep(5)

cancelmoose_thread = threading.Thread(target=cancelmoose, name="cancelmoose")
cancelmoose_thread.daemon = True
cancelmoose_thread.start()


def saver():
    global events
    global event_handlers
    while 1:
        for i in events:
            i.save()
        for i in event_handlers:
            i.save()
        time.sleep(5)

saver_thread = threading.Thread(target=saver, name="saver")
saver_thread.daemon = True
saver_thread.start()


def parser(client, userdata, msg):
    global log
    global messages
    global events
    global to_cancel
    messages += 1
    log += [{"topic": msg.topic, "payload": msg.payload}]
    if messages == conf["limit_to_save"] + 1:
        messages = 0
        json.dump({"log": log}, open(conf["path_to_log"], "w"))
        json.dump({"events": events}, open(conf["path_to_event_list"], "w"))
    if msg.topic == conf["data_chan"]:
        open(conf["path_to_data_folder"] + msg.payload.partition(
            "::")[0], "w").write(msg.payload.partition("::")[2])
    elif msg.topic == conf["event_chan"]:
        message = json.loads(msg.payload)
        message.update({"timestamp": time.time()})
        message = Event(message)
        if conf["debug"]:
            print("Recieved event of level", str(message.level),
                  "from user ID", message.uuid, "at ",
                  str(message.location) + ", which was assigned ID",
                  message.euid)
        events += [message]
    elif msg.topic == conf["cancel_chan"]:
        for i in events:
            if msg.payload.split("::")[0] == i.uuid and \
               msg.payload.split("::")[1] == i.euid:
                to_cancel.extend([i])
m.on_message = parser
m.loop_forever()
