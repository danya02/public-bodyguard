#!/usr/bin/python3
#    mobile-client.py - Event creator and sender
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


import threading
import time
import gps
import gpiozero
import paho.mqtt.client as mqtt
import uuid
import json
ADDRESS = "127.0.0.1"
global uid
try:
    uid = open("uuid.txt").read()
except:
    uid = str(uuid.uuid4())
    open("uuid.txt", "w").write(uid)


class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.session = gps.gps(mode=gps.WATCH_ENABLE)
        self.current_value = None

    def get_current_value(self):
        return self.current_value

    def run(self):
        try:
            while True:
                self.current_value = self.session.next()
                time.sleep(0.2)
        except StopIteration:
            pass


btn = gpiozero.Button(7, False)
m = mqtt.Client()
gpspoll = GpsPoller()
m.connect(ADDRESS)
global presses
global timed
timed = False
level = 0
presses = 0
last_time = 0


def timer():
    global presses
    global timed
    timed = True
    time.sleep(5)
    level = presses
    timed = False
    send_event(level)


def press():
    global presses
    global timed
    if not timed:
        threading.Thread(target=timer).start()
    presses += 1
btn.when_pressed = press


def send_event(level):
    global uid
    event = {"uuid": uid, "euid": uuid.uuid1(), "level": level, "location": [gpspoll.fix.latitude, gpspoll.fix.longitude, gpspoll.fix.alltitude, gpspoll.fix.accuracy]}
    m.publish(json.load(open("config.json"))["event_chan"], json.dumps(event), int(json.load(open("config.json"))["qos_level"]))
while 1:
    pass
