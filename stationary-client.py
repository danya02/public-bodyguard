#!/usr/bin/python
#    stationary-client.py - Event reciever and processor
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
import subprocess
import requests
import json
import uuid
import os
import geopy
import geopy.distance
from gpiozero import Button
m = mqtt.Client()
m.connect("127.0.0.1")
global uid
try:
    uid = open("uuid.txt").read()
except:
    uid = str(uuid.uuid4())
    open("uuid.txt", "w").write(uid)
self_lat = 55.806162385322
self_long = 37.542187524385
conf = {"l1": 500, "l2": 500, "l3": 500}
accept = Button(20)
decline = Button(21)


class MapGenerator:
    def __init__(self, pt, meta):
        if not isinstance(pt, list):
            raise TypeError("Expected <type 'list'>, got "+str(type(pt))+" instead")
        if not isinstance(meta, dict):
            raise TypeError("Expected <type 'dict'>, got "+str(type(meta))+" instead")
        self.points = pt
        self.meta = meta

    def get_file(self):
        addr = "http://static-maps.yandex.ru/1.x/?"
        addr = addr+"l="+str(self.meta["type"])+"&size="+str(self.meta["width"])+","+str(self.meta["height"])+"&lang="+str(self.meta["lang"])+"&pt="
        for i, j in zip(self.points, range(len(self.points)+1)[1:]):
            addr = addr+str(i["lat"])+","+str(i["long"])+","+str(i["style"])+str(i["color"])+str(i["size"])+str(i["content"])
            if not j == len(self.points):
                addr = addr+"~"
        open("/tmp/img.png", "wb").write(requests.get(addr).content)
        return "/tmp/img.png"


class PicDisplayer:
    def __init__(self, pic, fb="/dev/fb0"):
        self.viewer = subprocess.Popen(["sudo", "fbi", str(pic), "-a", "-d", str(fb)])
        self.alive = True

    def stop(self):
        if not self.alive:
            raise RuntimeError("Attempted to stop a stopped client")
        os.popen("killall fbi").read()
        self.alive = False
m.subscribe("/user/events")
m.subscribe("/user/cancel")


def distance(point1, point2):
    return geopy.distance.vincenty(point1[:2], point2[:2]).meters


def parser(client, userdata, message):
    global uid
    global p
    if message.topic == "/user/cancel":
        payload = message.payload
        payload = str(payload)
        p.uuid = str(p.uuid)
        p.euid = str(p.euid)
        print(payload)
        if str(payload.split("::")[0]) == str(p.uuid) and str(payload.split("::")[1]) == str(p.euid):
            try:
                p.stop()
                # magic.gpio.display("Event resolved")
                # time.sleep(5)
                # magic.gpio.display("")
                p = None
            except:
                pass
    elif message.topic == "/user/events":
        payload = json.loads(message.payload)
        if not distance([self_lat, self_long], payload["location"]) > conf["l"+str(payload["level"])]:
            m = MapGenerator([{"lat": self_lat, "long": self_long, "style": "round", "color": "", "size": "", "content": ""},
                              {"lat": payload["location"][0], "long": payload["location"][1], "color": "rd", "style": "pm2", "size": "l", "content":""}],
                             {"lang": "ru_RU", "width": 320, "height": 240, "type": "map"}).get_file()
            p = PicDisplayer(m)
            p.euid = payload["euid"]
            p.uuid = payload["uuid"]
        # magic.gpio.display("Event nearby")
        while (not accept.is_pressed) or (not decline.is_pressed):
            pass
        if accept.is_pressed:
            client.publish("/user/replies", uid+"@"+payload["euid"]+"::1")
        elif decline.is_pressed:
            client.publish("/user/replies", uid+"@"+payload["euid"]+"::0")
            # magic.gpio.display("")
            p.stop()
m.on_message = parser
m.loop_forever()
