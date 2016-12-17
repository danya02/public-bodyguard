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
import random
import gpsd
import os
import paho.mqtt.client as mqtt
import uuid
import json
try:
    import gpiozero
    IS_A_PI = True
except:
    print("gpiozero not installed, defaulting to non-RPi behaviour")
    IS_A_PI = False
ADDRESS = "127.0.0.1"
INITPLACE = [55.806162385322, 37.542187524385, 500, 10]
global uid
try:
    uid = open("uuid.txt").read()
except:
    uid = str(uuid.uuid4())
    open("uuid.txt", "w").write(uid)
conf = json.load(open("config.json"))


class Void:
    pass


class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        try:
            gpsd.connect()
        except:
            os.popen("sudo gpsd /dev/ttyUSB0")
            time.sleep(2)
            gpsd.connect()
        for i in ["latitude", "longitude", "altitude", "accuracy"]:
            object.__setattr__(self, i, 0)

    def run(self):
        while 1:
            try:

                data = gpsd.get_current()
                self.latitude = data.lat
                self.longitude = data.lon
                self.altitude = data.alt
                self.latitude = data.lat
                self.accuracy = data.position_precision()[0]
                time.sleep(1)
            except:
                pass


class FakeGpsPoller(threading.Thread):
    def run(self):
        while 1:
            time.sleep(random.random())
            offseth = random.randint(1, 20) * 0.01
            offsetv = random.randint(1, 4) * 0.5
            offseta = random.randint(1, 2) * 5
            if random.randint(0, 1):
                offseth = offseth * -1
            if random.randint(0, 1):
                offsetv = offsetv * -1
            if random.randint(0, 1):
                offseta = offseta * -1
            self.latitude += offseth
            self.longitude -= offseth
            self.altitude += offsetv
            self.accuracy += offseta
            if self.accuracy < 0:
                self.accuracy = 10
            if self.altitude < 0:
                self.altitude = 10

    def __init__(self, loc):
        threading.Thread.__init__(self)
        self.daemon = True

        self.latitude = loc[0]
        self.longitude = loc[1]
        self.altitude = loc[2]
        self.accuracy = loc[3]


class FakeButton(threading.Thread):
    def run(self):
        while 1:
            input()
            if callable(self.when_pressed):
                self.when_pressed()

    def __init__(self):
        threading.Thread.__init__(self)
        self.when_pressed = None
        self.daemon = True
        self.start()

if IS_A_PI:
    btn = gpiozero.Button(7, False)
else:
    btn = FakeButton()
m = mqtt.Client()
try:
    gpspoll = GpsPoller()
except:
    assert(conf["debug"])
    print("-----WARNING-----", "No GPS module detected.",
          "This program will work in simulation mode.", sep="\n")
    gpspoll = FakeGpsPoller(INITPLACE)
gpspoll.start()
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
    presses = 0


def press():
    global presses
    global timed
    if not timed:
        threading.Thread(target=timer).start()
    presses += 1
btn.when_pressed = press


def send_event(level):
    global uid
    event = {"uuid": uid, "euid": str(uuid.uuid1()), "level": level,
             "location": [gpspoll.latitude, gpspoll.longitude,
                          gpspoll.altitude, gpspoll.accuracy]}
    m.publish(conf["event_chan"], payload=json.dumps(event))
while 1:
    pass
