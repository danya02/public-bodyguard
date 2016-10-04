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
import gpiozero
import paho.mqtt.client as mqtt
import uuid
import json
ADDRESS = "127.0.0.1"
INITPLACE = [55.806162385322, 37.542187524385, 500, 10]
global uid
try:
    uid = open("uuid.txt").read()
except:
    uid = str(uuid.uuid4())
    open("uuid.txt", "w").write(uid)


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

    def run(self):
        while 1:
            try:
                self.fix = Void()
                data = gpsd.get_current()
                self.fix.latitude = data.lat
                self.fix.longitude = data.lon
                self.fix.altitude = data.alt
                self.fix.latitude = data.lat
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
                offseth = offseth * -1
            self.fix.latitude += offseth
            self.fix.longitude -= offseth
            self.fix.altitude += offsetv
            self.accuracy += offseta
            if self.fix.accuracy < 0:
                self.fix.accuracy = 10
            if self.fix.altitude < 0:
                self.fix.altitude = 10

    def __init__(self, loc):
        threading.Thread.__init__(self)
        self.daemon = True
        self.fix = Void()
        self.fix.latitude = loc[0]
        self.fix.longitude = loc[1]
        self.fix.altitude = loc[2]
        self.fix.accuracy = loc[3]
btn = gpiozero.Button(7, False)
m = mqtt.Client()
try:
    gpspoll = GpsPoller()
except:
    print("-----WARNING-----\nNo GPS module detected.\nThis program will work in simulation mode.")
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


def press():
    global presses
    global timed
    if not timed:
        threading.Thread(target=timer).start()
    presses += 1
btn.when_pressed = press


def send_event(level):
    global uid
    event = {"uuid": uid, "euid": uuid.uuid1(), "level": level, "location": [gpspoll.fix.latitude, gpspoll.fix.longitude, gpspoll.fix.altitude, gpspoll.fix.accuracy]}
    m.publish(json.load(open("config.json"))["event_chan"], json.dumps(event), int(json.load(open("config.json"))["qos_level"]))
while 1:
    pass
