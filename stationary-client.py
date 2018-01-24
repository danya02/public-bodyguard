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


try:
    import RPi.GPIO
    THIS_PI = True
except ImportError:
    THIS_PI = False

import paho.mqtt.client as mqtt
import subprocess
import urllib.request
import json
import uuid
import os
import geopy
import geopy.distance
import threading

if THIS_PI:
    from gpiozero import Button
else:
    import pygame
m = mqtt.Client()
m.connect("127.0.0.1")
global uid
try:
    uid = open("uuid.txt").read()
except FileNotFoundError:
    uid = str(uuid.uuid4())
    open("uuid.txt", "w").write(uid)
self_lat = 55.806162385322
self_long = 37.542187524385
conf = {"l1": 50000000, "l2": 500000000, "l3": 500000000}
if not THIS_PI:
    pygame.init()

class PygameButton(threading.Thread):
    def __init__(self, keys):
        super().__init__()
        self.name = 'Pygame key capturer looking at keys {}'.format(keys)
        self.daemon = True
        self.keys = keys
        self.is_pressed = False
        self.start()

    def run(self):
        while 1:
            pygame.time.delay(100)
            self.is_pressed = False
            k = pygame.key.get_pressed()
            for i in self.keys:
                self.is_pressed &= k[i]


if THIS_PI:
    accept = Button(20)
    decline = Button(21)
else:
    accept = PygameButton([pygame.K_RETURN, pygame.K_y, pygame.K_SPACE])
    decline = PygameButton([pygame.K_ESCAPE, pygame.K_n, pygame.K_BREAK])


class MapGenerator:
    def __init__(self, pt, meta):
        if not isinstance(pt, list):
            raise TypeError("Expected <type 'list'>, got " + str(type(pt)) +
                            " instead")
        if not isinstance(meta, dict):
            raise TypeError("Expected <type 'dict'>, got " + str(type(meta)) +
                            " instead")
        self.points = pt
        self.meta = meta

    def get_file(self):
        addr = "http://static-maps.yandex.ru/1.x/?"
        addr += "l=" + str(self.meta["type"]) + "&size="
        addr += str(self.meta["width"]) + "," + str(self.meta["height"])
        addr += "&lang=" + str(self.meta["lang"]) + "&pt="
        for i, j in zip(self.points, range(len(self.points) + 1)[1:]):
            addr += str(i["lat"]) + "," + str(i["long"]) + ","
            addr += str(i["style"]) + str(i["color"]) + str(i["size"])
            addr += str(i["content"])
            if not j == len(self.points):
                addr = addr + "~"
        with open(
                "/tmp/img.png", "wb") as o, urllib.request.urlopen(addr) as i:
            o.write(i.read())
        return "/tmp/img.png"

    def __str__(self):
        return self.get_file()


class PicDisplayerFbi:
    def __init__(self, pic, fb="/dev/fb0"):
        self.viewer = subprocess.Popen(["sudo", "fbi", str(pic), "-a", "-d",
                                        str(fb), "-noverbose"])
        self.alive = True

    def stop(self):
        if not self.alive:
            raise RuntimeError("Attempted to stop a stopped client")
        os.popen("killall fbi").read()
        self.alive = False


class PicDisplayerPygame:
    def __init__(self, pic):
        self.alive = True
        self.pic = pygame.image.load(pic)
        self.screen = pygame.display.set_mode(self.pic.get_size())
        self.screen.blit(self.pic, (0, 0))
        pygame.display.flip()

    def stop(self):
        if not self.alive:
            raise RuntimeError("Attempted to stop a stopped client")
        pygame.display.set_mode((1,1))
        self.alive = False


m.subscribe("/user/events")
m.subscribe("/user/cancel")


def distance(point1, point2):
    return geopy.distance.vincenty(point1[:2], point2[:2]).meters


def parser(client, userdata, message):
    global uid
    global p
    print(message.payload)
    if message.topic == "/user/cancel":
        payload = message.payload
        payload = str(payload)
        p.uuid = str(p.uuid)
        p.euid = str(p.euid)
        print(payload)
        if str(payload.split("::")[0]) == str(p.uuid) and str(payload.split(
                "::")[1]) == str(p.euid):
            try:
                p.stop()
                # magic.gpio.display("Event resolved")
                # time.sleep(5)
                # magic.gpio.display("")
                p = None
            except:
                pass
    elif message.topic == "/user/events":
        try:
            payload = json.loads(message.payload)
        except:
            payload = json.loads(str(message.payload, "utf8"))
        if not distance([self_lat, self_long],
                        payload["location"]) > conf["l" +
                str(payload["level"])]:
            m = MapGenerator([{"lat": self_lat, "long": self_long,
                               "style": "round", "color": "", "size": "",
                               "content": ""}, {"lat": payload["location"][0],
                                                "long": payload["location"][1],
                                                "color": ["rd","or","gn"][payload["level"]-1], "style": "pm2",
                                                "size": "l", "content": ""}],
                             {"lang": "ru_RU", "width": 320 if THIS_PI else 650, "height": 240 if THIS_PI else 450,
                              "type": "map"}).get_file()
            if THIS_PI:
                p = PicDisplayerFbi(m)
            else:
                p = PicDisplayerPygame(m)
            p.euid = payload["euid"]
            p.uuid = payload["uuid"]
        # magic.gpio.display("Event nearby")
#        while (not accept.is_pressed) or (not decline.is_pressed):
#            pass
#        if accept.is_pressed:
#            client.publish("/user/replies", uid + "@" + payload["euid"] + "::1")
#        elif decline.is_pressed:
#            client.publish("/user/replies", uid + "@" + payload["euid"] + "::0")
#            # magic.gpio.display("")
#            p.stop()


m.on_message = parser
m.loop_forever()
