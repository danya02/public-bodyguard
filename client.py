#!/usr/bin/python3
#    client.py - Event creator and sender
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


class Button:
        def __init__(self, pin, notgnd):
                import RPi.GPIO
                import threading
                self._gpio = RPi.GPIO
                self._pin_ = pin
                self._gpio.setmode(self._gpio.BOARD)
                self._gpio.setwarnings(False)
                self.callback_true = None
                self.callback_false = None
                self._gpio.setup(self._pin_, self._gpio.IN, (self._gpio.PUD_UP
                                                             if not notgnd else
                                                             self._gpio.PUD_DOWN
                                                             ))
                self.__thread = threading.Thread(target=self.polling)
                self.__thread.start()

        def state(self):
                self._gpio.setmode(self._gpio.BOARD)
                self._gpio.setwarnings(False)
                self._gpio.setup(self._pin_, self._gpio.IN, self._gpio.PUD_UP)
                return self._gpio.input(self._pin_)

        def wait_for(self, which):
                self._gpio.wait_for_edge(self._pin_, which)

        def polling(self):
            while 1:
                self.wait_for(True)
                if not isinstance(self.callback_true, None):
                    self.callback_true()
                self.wait_for(False)
                if not isinstance(self.callback_false, None):
                    self.callback_false()
btn = Button(7, False)
m = mqtt.Client()
gpspoll = GpsPoller()
m.connect(ADDRESS)
global last_time
global presses
global level
global timed
timed = False
level = 0
presses = 0
last_time = 0


def timer():
    global last_time
    global level
    global timed
    timed = True
    while not last_time+5 < time.time():
        pass
    level = presses
    timed = False
    send_event(level)


def press():
    global last_time
    global presses
    global timed
    if not timed:
        threading.Thread(target=timer).start()
    presses += 1
    last_time = time.time()


def send_event(level):
    global uid
    event = {"uuid": uid, "euid": uuid.uuid1(), "level": level, "location": [gpspoll.fix.latitude, gpspoll.fix.longitude, gpspoll.fix.alltitude, gpspoll.fix.accuracy]}
    m.publish(json.load(open("config.json"))["event_chan"], json.dumps(event))
